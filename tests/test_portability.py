"""Backup e exportação com conteúdo fictício em diretórios temporários."""

import csv
import hashlib
import json
import tempfile
import unittest
import zipfile
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path

from finance_app.domain.models import Account, Category, Transaction
from finance_app.storage.csv_store import CsvStore, StorageError
from finance_app.storage.portability import CsvPortability, MANIFEST_NAME


class PortabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.store = CsvStore(self.data)
        self.account = self.store.create(Account("Conta fictícia", "bank"))
        self.category = self.store.create(Category("Alimentação", "expense"))
        self.transaction = self.store.create(Transaction(
            "expense", "Café com pão", Decimal("1234.50"), date(2026, 10, 1),
            self.category.id, self.account.id,
        ))
        self.portability = CsvPortability(self.data)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_backup_restore_and_csv_export_preserve_utf8_and_decimal_text(self) -> None:
        backup = self.portability.create_backup(self.root / "backup.zip")
        export = self.portability.export_csv(self.root / "export.zip")
        with zipfile.ZipFile(export) as archive:
            raw = archive.read("transactions.csv")
            self.assertIn("Café com pão".encode("utf-8"), raw)
            rows = list(csv.DictReader(StringIO(raw.decode("utf-8"))))
            self.assertEqual(rows[0]["amount"], "1234.50")
            self.assertNotIn(MANIFEST_NAME, archive.namelist())

        changed = Transaction(
            self.transaction.kind, "Descrição alterada", self.transaction.amount,
            self.transaction.date, self.transaction.category_id,
            self.transaction.account_id, id=self.transaction.id,
        )
        self.store.update(changed)
        self.portability.restore_backup(backup)
        reopened = CsvStore(self.data)
        restored = reopened.get(Transaction, self.transaction.id)
        self.assertEqual(restored.description, "Café com pão")
        self.assertEqual(restored.amount, Decimal("1234.50"))

    def test_invalid_relationship_is_rejected_before_live_files_change(self) -> None:
        original = self.portability.create_backup(self.root / "valid.zip")
        invalid = self.root / "invalid.zip"
        with zipfile.ZipFile(original) as archive:
            members = {name: archive.read(name) for name in archive.namelist()}
        bad_csv = members["transactions.csv"].replace(
            self.account.id.encode("utf-8"), b"missing-account-id",
        )
        members["transactions.csv"] = bad_csv
        manifest = json.loads(members[MANIFEST_NAME].decode("utf-8"))
        manifest["files"]["transactions.csv"] = hashlib.sha256(bad_csv).hexdigest()
        members[MANIFEST_NAME] = json.dumps(manifest).encode("utf-8")
        with zipfile.ZipFile(invalid, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, contents in members.items(): archive.writestr(name, contents)

        with self.assertRaisesRegex(StorageError, "não existe"):
            self.portability.restore_backup(invalid)
        self.assertEqual(self.store.get(Transaction, self.transaction.id).description, "Café com pão")

    def test_export_cannot_overwrite_an_application_csv(self) -> None:
        with self.assertRaisesRegex(StorageError, "arquivo de dados"):
            self.portability.export_csv(self.data / "accounts.csv")


if __name__ == "__main__":
    unittest.main()
