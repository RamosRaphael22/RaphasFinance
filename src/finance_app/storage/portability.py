"""Backup, restauração validada e exportação de pacotes CSV."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from finance_app.storage.csv_store import CsvStore, StorageError
from finance_app.storage.schemas import ENCODING, TABLES

BACKUP_FORMAT = "raphasbank-csv-backup"
BACKUP_VERSION = 1
MANIFEST_NAME = "manifest.json"
MAX_CSV_SIZE = 200 * 1024 * 1024


class CsvPortability:
    """Move CSV data between the app and user-selected archive files."""

    def __init__(self, data_directory: Path | str) -> None:
        self.data_directory = Path(data_directory)

    def create_backup(self, destination: Path | str) -> Path:
        destination = self._guard_destination(destination)
        files = self._read_current_files()
        manifest = {
            "format": BACKUP_FORMAT,
            "version": BACKUP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": {name: hashlib.sha256(contents).hexdigest()
                      for name, contents in sorted(files.items())},
        }
        members = dict(files)
        members[MANIFEST_NAME] = json.dumps(
            manifest, ensure_ascii=False, indent=2,
        ).encode(ENCODING)
        return self._write_archive(destination, members)

    def export_csv(self, destination: Path | str) -> Path:
        """Export a ZIP of separate UTF-8 CSVs without a restore manifest."""
        destination = self._guard_destination(destination)
        return self._write_archive(destination, self._read_current_files())

    def restore_backup(self, source: Path | str) -> None:
        source = Path(source)
        names = [spec.filename for spec in TABLES.values()]
        try:
            with zipfile.ZipFile(source, "r") as archive:
                members = self._validate_archive_members(archive, set(names) | {MANIFEST_NAME})
                if MANIFEST_NAME not in members:
                    raise StorageError("O arquivo selecionado não é um backup reconhecido.")
                manifest = self._read_manifest(archive, members[MANIFEST_NAME], set(names))
                contents = {}
                for name in names:
                    info = members.get(name)
                    if info is None:
                        raise StorageError(f"Backup incompleto: arquivo {name} ausente.")
                    if info.file_size > MAX_CSV_SIZE:
                        raise StorageError(f"Backup inválido: {name} excede o tamanho permitido.")
                    raw = archive.read(info)
                    if hashlib.sha256(raw).hexdigest() != manifest["files"][name]:
                        raise StorageError(f"Backup inválido: verificação de integridade falhou em {name}.")
                    contents[name] = raw
        except StorageError:
            raise
        except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
            raise StorageError(f"Não foi possível ler o backup: {exc}.") from exc

        self.data_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".finance-restore-",
                                         dir=self.data_directory.parent) as temporary:
            staging = Path(temporary) / "validated"
            staging.mkdir()
            for name, raw in contents.items():
                (staging / name).write_bytes(raw)
            candidate = CsvStore(staging)
            for model in TABLES:
                candidate.list(model)
            self._replace_current_files(staging, names)

    def _read_current_files(self) -> dict[str, bytes]:
        store = CsvStore(self.data_directory)
        files = {}
        for model, spec in TABLES.items():
            store.list(model)
            path = self.data_directory / spec.filename
            try:
                files[spec.filename] = path.read_bytes()
            except OSError as exc:
                raise StorageError(f"Não foi possível exportar {spec.filename}: {exc}.") from exc
        return files

    def _guard_destination(self, destination: Path | str) -> Path:
        destination = Path(destination).resolve()
        protected = {(self.data_directory / spec.filename).resolve() for spec in TABLES.values()}
        if destination in protected:
            raise StorageError("O destino escolhido é um arquivo de dados do aplicativo.")
        return destination

    @staticmethod
    def _validate_archive_members(archive: zipfile.ZipFile, allowed: set[str]):
        members = {}
        for info in archive.infolist():
            name = info.filename
            if info.is_dir() or Path(name).name != name or name not in allowed:
                raise StorageError(f"Arquivo ZIP contém um caminho ou arquivo não permitido: {name!r}.")
            if name in members:
                raise StorageError(f"Arquivo ZIP contém arquivo duplicado: {name}.")
            members[name] = info
        return members

    @staticmethod
    def _read_manifest(archive: zipfile.ZipFile, info: zipfile.ZipInfo,
                       expected_files: set[str]) -> dict:
        if info.file_size > 64 * 1024:
            raise StorageError("Manifesto do backup inválido ou muito grande.")
        try:
            manifest = json.loads(archive.read(info).decode(ENCODING))
        except (UnicodeDecodeError, json.JSONDecodeError, RuntimeError) as exc:
            raise StorageError("Manifesto do backup inválido.") from exc
        if (not isinstance(manifest, dict)
                or manifest.get("format") != BACKUP_FORMAT
                or manifest.get("version") != BACKUP_VERSION
                or not isinstance(manifest.get("files"), dict)
                or set(manifest["files"]) != expected_files
                or any(not isinstance(value, str) or len(value) != 64
                       for value in manifest["files"].values())):
            raise StorageError("Formato ou conteúdo do manifesto do backup não é compatível.")
        return manifest

    def _replace_current_files(self, staging: Path, names: list[str]) -> None:
        previous = {name: (self.data_directory / name).read_bytes()
                    for name in names if (self.data_directory / name).exists()}
        replaced = []
        try:
            for name in names:
                os.replace(staging / name, self.data_directory / name)
                replaced.append(name)
        except OSError as exc:
            rollback_errors = []
            for name in reversed(replaced):
                try:
                    original = previous.get(name)
                    if original is None:
                        (self.data_directory / name).unlink(missing_ok=True)
                    else:
                        temporary = self.data_directory / f".{name}.{uuid4().hex}.rollback"
                        temporary.write_bytes(original)
                        os.replace(temporary, self.data_directory / name)
                except OSError as rollback_exc:
                    rollback_errors.append(f"{name}: {rollback_exc}")
            detail = (f" A reversão também encontrou erros: {', '.join(rollback_errors)}."
                      if rollback_errors else " Os dados anteriores foram preservados.")
            raise StorageError(f"Não foi possível concluir a restauração: {exc}.{detail}") from exc

    @staticmethod
    def _write_archive(destination: Path | str, members: dict[str, bytes]) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, contents in sorted(members.items()):
                    archive.writestr(name, contents)
            os.replace(temporary, destination)
            return destination
        except (OSError, zipfile.BadZipFile) as exc:
            raise StorageError(f"Não foi possível gravar o arquivo {destination}: {exc}.") from exc
        finally:
            temporary.unlink(missing_ok=True)
