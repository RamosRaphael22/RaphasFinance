"""Armazenamento CSV com validação e substituição atômica."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from dataclasses import replace
from typing import TypeVar
from uuid import uuid4

from finance_app.domain.models import (Account, Budget, Category, Goal, RecurrenceOccurrence,
                                       RecurrenceRule, Transaction, Transfer, Wish)
from finance_app.domain.validation import ValidationError, validate
from finance_app.storage.schemas import (
    DELIMITER,
    ENCODING,
    LEGACY_ACCOUNT_COLUMNS,
    LEGACY_ACCOUNT_SPEC,
    LEGACY_TRANSACTION_COLUMNS,
    LEGACY_TRANSACTION_SPEC,
    LINE_TERMINATOR,
    TABLES,
    SchemaError,
)

Record = TypeVar("Record", Account, Category, Transaction, Transfer, Wish, Goal, Budget,
                 RecurrenceRule, RecurrenceOccurrence)


class StorageError(ValueError):
    """Erro de leitura, integridade ou gravação com contexto do arquivo."""


class CsvStore:
    """Persiste contas, categorias e lançamentos em arquivos CSV locais."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        for model, spec in TABLES.items():
            path = self.directory / spec.filename
            if not path.exists():
                self._write(path, spec, [])
            elif model is Account:
                self._migrate_accounts(path)
            elif model is Transaction:
                self._migrate_transactions(path)

    def list(self, model: type[Record]) -> list[Record]:
        spec = self._spec(model)
        records = self._read(spec)
        transactions = records if model is Transaction else self._read(TABLES[Transaction])
        transfers = records if model is Transfer else self._read(TABLES[Transfer])
        self._validate_relations(transactions, transfers)
        return records

    def get(self, model: type[Record], record_id: str) -> Record | None:
        return next((item for item in self.list(model) if item.id == record_id), None)

    def create(self, record: Record) -> Record:
        spec = self._spec(type(record))
        validate(record)
        records = self._read(spec)
        if any(item.id == record.id for item in records):
            raise StorageError(f"{spec.filename}: identificador duplicado {record.id!r}.")
        records.append(record)
        transactions = records if isinstance(record, Transaction) else self._read(TABLES[Transaction])
        transfers = records if isinstance(record, Transfer) else self._read(TABLES[Transfer])
        occurrences = records if isinstance(record, RecurrenceOccurrence) else self._read(TABLES[RecurrenceOccurrence])
        self._validate_relations(transactions, transfers, occurrences)
        self._write(self.directory / spec.filename, spec, records)
        return record

    def update(self, record: Record) -> Record:
        spec = self._spec(type(record))
        validate(record)
        records = self._read(spec)
        for index, current in enumerate(records):
            if current.id == record.id:
                records[index] = record
                break
        else:
            raise StorageError(f"{spec.filename}: registro {record.id!r} não encontrado.")
        transactions = records if isinstance(record, Transaction) else self._read(TABLES[Transaction])
        transfers = records if isinstance(record, Transfer) else self._read(TABLES[Transfer])
        occurrences = records if isinstance(record, RecurrenceOccurrence) else self._read(TABLES[RecurrenceOccurrence])
        self._validate_relations(transactions, transfers, occurrences)
        self._write(self.directory / spec.filename, spec, records)
        return record

    def delete(self, model: type[Record], record_id: str) -> None:
        spec = self._spec(model)
        records = self._read(spec)
        remaining = [item for item in records if item.id != record_id]
        if len(remaining) == len(records):
            raise StorageError(f"{spec.filename}: registro {record_id!r} não encontrado.")
        transactions = self._read(TABLES[Transaction])
        transfers = self._read(TABLES[Transfer])
        updated_transactions = remaining if model is Transaction else transactions
        updated_transfers = remaining if model is Transfer else transfers
        updated_occurrences = remaining if model is RecurrenceOccurrence else self._read(TABLES[RecurrenceOccurrence])
        if model is RecurrenceRule:
            # Preserve confirmed entries as ordinary transactions after their rule is removed.
            updated_transactions = [
                replace(item, recurrence_id="", recurrence_date=None)
                if item.recurrence_id == record_id else item
                for item in transactions
            ]
            updated_occurrences = [
                item for item in self._read(TABLES[RecurrenceOccurrence])
                if item.rule_id != record_id
            ]
        self._validate_relations(updated_transactions, updated_transfers, updated_occurrences)
        if model is Account and any(item.account_id == record_id for item in transactions):
            raise StorageError("accounts.csv: conta em uso por lançamentos; desative-a em vez de excluir.")
        if model is Category and any(item.category_id == record_id for item in transactions):
            raise StorageError("categories.csv: categoria em uso por lançamentos; desative-a em vez de excluir.")
        if model is Category and any(item.category_id == record_id for item in self._read(TABLES[Budget])):
            raise StorageError("categories.csv: categoria em uso por orçamento; desative-a em vez de excluir.")
        if model is Account and any(
            item.source_account_id == record_id or item.destination_account_id == record_id
            for item in transfers
        ):
            raise StorageError("accounts.csv: conta em uso por transferências; desative-a em vez de excluir.")
        if model is Account and any(item.account_id == record_id for item in self._read(TABLES[RecurrenceRule])):
            raise StorageError("accounts.csv: conta usada por recorrência; desative-a em vez de excluir.")
        if model is Category and any(item.category_id == record_id for item in self._read(TABLES[RecurrenceRule])):
            raise StorageError("categories.csv: categoria usada por recorrência; desative-a em vez de excluir.")
        if model is RecurrenceRule:
            self._write(self.directory / TABLES[Transaction].filename, TABLES[Transaction], updated_transactions)
            self._write(self.directory / TABLES[RecurrenceOccurrence].filename, TABLES[RecurrenceOccurrence], updated_occurrences)
        self._write(self.directory / spec.filename, spec, remaining)

    def _read(self, spec):
        path = self.directory / spec.filename
        try:
            with path.open("r", encoding=ENCODING, newline="") as file:
                reader = csv.DictReader(file, delimiter=DELIMITER)
                if reader.fieldnames != list(spec.columns):
                    raise StorageError(
                        f"{spec.filename}, cabeçalho: esperado {list(spec.columns)!r}, "
                        f"recebido {reader.fieldnames!r}."
                    )
                records = []
                for line, row in enumerate(reader, start=2):
                    if None in row or any(value is None for value in row.values()):
                        raise StorageError(f"{spec.filename}, registro {line}: quantidade de colunas incorreta.")
                    try:
                        record = spec.parse(row)
                        validate(record)
                    except (SchemaError, ValidationError) as exc:
                        raise StorageError(f"{spec.filename}, registro {line}: {exc}") from exc
                    if any(item.id == record.id for item in records):
                        raise StorageError(f"{spec.filename}, registro {line}: identificador duplicado {record.id!r}.")
                    records.append(record)
                return records
        except UnicodeDecodeError as exc:
            raise StorageError(f"{spec.filename}: arquivo não está codificado em UTF-8.") from exc
        except OSError as exc:
            raise StorageError(f"{spec.filename}: não foi possível ler o arquivo: {exc}.") from exc

    def _migrate_accounts(self, path: Path) -> None:
        try:
            with path.open("r", encoding=ENCODING, newline="") as file:
                header = next(csv.reader(file, delimiter=DELIMITER), None)
        except (OSError, UnicodeDecodeError) as exc:
            raise StorageError(f"accounts.csv: não foi possível verificar o esquema: {exc}.") from exc
        if header == list(LEGACY_ACCOUNT_COLUMNS):
            accounts = self._read(LEGACY_ACCOUNT_SPEC)
            self._write(path, TABLES[Account], accounts)

    def _migrate_transactions(self, path: Path) -> None:
        try:
            with path.open("r", encoding=ENCODING, newline="") as file:
                header = next(csv.reader(file, delimiter=DELIMITER), None)
        except (OSError, UnicodeDecodeError) as exc:
            raise StorageError(f"transactions.csv: não foi possível verificar o esquema: {exc}.") from exc
        if header == list(LEGACY_TRANSACTION_COLUMNS):
            transactions = self._read(LEGACY_TRANSACTION_SPEC)
            self._write(path, TABLES[Transaction], transactions)

    def _write(self, path: Path, spec, records) -> None:
        temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            with temporary_path.open("x", encoding=ENCODING, newline="") as file:
                writer = csv.DictWriter(
                    file, fieldnames=spec.columns, delimiter=DELIMITER,
                    lineterminator=LINE_TERMINATOR,
                )
                writer.writeheader()
                for record in records:
                    writer.writerow(spec.serialize(record))
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, path)
        except OSError as exc:
            raise StorageError(f"{path.name}: não foi possível gravar com segurança: {exc}.") from exc
        finally:
            if temporary_path.exists():
                temporary_path.unlink(missing_ok=True)

    def _validate_relations(self, transactions: list[Transaction], transfers: list[Transfer],
                            occurrences: list[RecurrenceOccurrence] | None = None) -> None:
        accounts = {item.id: item for item in self._read(TABLES[Account])}
        categories = {item.id: item.kind for item in self._read(TABLES[Category])}
        rules = {item.id: item for item in self._read(TABLES[RecurrenceRule])}
        for index, rule in enumerate(rules.values(), start=2):
            account = accounts.get(rule.account_id)
            category_kind = categories.get(rule.category_id)
            if account is None or category_kind is None or category_kind != rule.kind:
                raise StorageError(
                    f"recurrence_rules.csv, registro {index}: conta ou categoria incompatível."
                )
        recurrence_keys: set[tuple[str, object]] = set()
        for index, item in enumerate(transactions, start=2):
            if item.account_id not in accounts:
                raise StorageError(f"transactions.csv, registro {index}: conta {item.account_id!r} não existe.")
            if item.category_id not in categories:
                raise StorageError(f"transactions.csv, registro {index}: categoria {item.category_id!r} não existe.")
            if categories[item.category_id] != item.kind:
                raise StorageError(f"transactions.csv, registro {index}: tipo não corresponde à categoria.")
            if item.recurrence_id:
                if item.recurrence_id not in rules:
                    raise StorageError(f"transactions.csv, registro {index}: regra de recorrência não existe.")
                key = (item.recurrence_id, item.recurrence_date)
                if key in recurrence_keys:
                    raise StorageError(f"transactions.csv, registro {index}: ocorrência recorrente duplicada.")
                recurrence_keys.add(key)
        for index, item in enumerate(transfers, start=2):
            source = accounts.get(item.source_account_id)
            destination = accounts.get(item.destination_account_id)
            if source is None or destination is None:
                raise StorageError(f"transfers.csv, registro {index}: conta de origem ou destino não existe.")
            if source.kind == "credit_card":
                raise StorageError(f"transfers.csv, registro {index}: cartão não pode ser origem da transferência.")
        budget_keys = set()
        for index, item in enumerate(self._read(TABLES[Budget]), start=2):
            if categories.get(item.category_id) != "expense":
                raise StorageError(f"budgets.csv, registro {index}: categoria de despesa não existe.")
            key = (item.category_id, item.period)
            if key in budget_keys:
                raise StorageError(f"budgets.csv, registro {index}: orçamento de categoria e mês duplicado.")
            budget_keys.add(key)
        occurrence_keys: set[tuple[str, object]] = set()
        occurrences = occurrences if occurrences is not None else self._read(TABLES[RecurrenceOccurrence])
        for index, item in enumerate(occurrences, start=2):
            if item.rule_id not in rules:
                raise StorageError(f"recurrence_occurrences.csv, registro {index}: regra não existe.")
            key = (item.rule_id, item.occurrence_date)
            if key in occurrence_keys:
                raise StorageError(f"recurrence_occurrences.csv, registro {index}: ocorrência duplicada.")
            occurrence_keys.add(key)

    @staticmethod
    def _spec(model: type):
        try:
            return TABLES[model]
        except KeyError as exc:
            raise TypeError(f"Modelo sem esquema CSV: {model!r}.") from exc
