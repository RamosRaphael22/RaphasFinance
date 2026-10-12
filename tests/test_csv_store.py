"""Testes da persistência com dados fictícios em diretórios temporários."""

import csv
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance_app.domain.models import Account, Category, Transaction
from finance_app.storage.csv_store import CsvStore, StorageError


class CsvStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.directory = Path(self.temporary.name)
        self.store = CsvStore(self.directory)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_missing_files_are_initialized_without_records(self) -> None:
        self.assertEqual(self.store.list(Account), [])
        self.assertEqual(self.store.list(Category), [])
        self.assertEqual(self.store.list(Transaction), [])
        with (self.directory / "transactions.csv").open(encoding="utf-8", newline="") as file:
            self.assertEqual(next(csv.reader(file)), [
                "kind", "description", "amount", "date", "category_id",
                "account_id", "notes", "id", "recurrence_id", "recurrence_date",
            ])

    def test_crud_round_trip_preserves_decimal_date_and_accents(self) -> None:
        account = self.store.create(Account("Carteira", "cash"))
        category = self.store.create(Category("Alimentação", "expense"))
        entry = self.store.create(Transaction(
            "expense", "Café", Decimal("12.30"), date(2026, 10, 11),
            category.id, account.id, "lanche",
        ))
        loaded = self.store.get(Transaction, entry.id)
        self.assertEqual(loaded, entry)
        self.assertIsInstance(loaded.amount, Decimal)
        self.assertIsInstance(loaded.date, date)

        updated = Transaction(
            entry.kind, "Café e pão", Decimal("15.70"), entry.date,
            entry.category_id, entry.account_id, entry.notes, entry.id,
        )
        self.store.update(updated)
        self.assertEqual(self.store.get(Transaction, entry.id), updated)
        self.store.delete(Transaction, entry.id)
        self.assertIsNone(self.store.get(Transaction, entry.id))

    def test_rejects_invalid_values_and_relationships(self) -> None:
        account = self.store.create(Account("Conta", "bank"))
        category = self.store.create(Category("Salário", "income"))
        with self.assertRaises(ValueError):
            self.store.create(Transaction(
                "expense", "Inválido", Decimal("-1"), date.today(),
                category.id, account.id,
            ))
        with self.assertRaisesRegex(ValueError, "Decimal"):
            self.store.create(Transaction(
                "income", "Valor impreciso", 0.1, date.today(),
                category.id, account.id,
            ))
        with self.assertRaisesRegex(StorageError, "não existe"):
            self.store.create(Transaction(
                "income", "Teste", Decimal("1"), date.today(),
                category.id, "conta-ausente",
            ))
        self.assertEqual(self.store.list(Transaction), [])

    def test_prevents_deleting_referenced_accounts_and_categories(self) -> None:
        account = self.store.create(Account("Conta", "bank"))
        category = self.store.create(Category("Transporte", "expense"))
        entry = self.store.create(Transaction(
            "expense", "Ônibus", Decimal("4"), date.today(), category.id, account.id,
        ))
        with self.assertRaisesRegex(StorageError, "conta em uso"):
            self.store.delete(Account, account.id)
        with self.assertRaisesRegex(StorageError, "categoria em uso"):
            self.store.delete(Category, category.id)
        self.assertEqual(self.store.get(Transaction, entry.id), entry)

    def test_deletes_unused_category(self) -> None:
        category = self.store.create(Category("Temporária", "expense"))

        self.store.delete(Category, category.id)

        self.assertIsNone(self.store.get(Category, category.id))

    def test_invalid_header_reports_file_and_does_not_overwrite_it(self) -> None:
        path = self.directory / "accounts.csv"
        original = "wrong,header\nkeep,this\n"
        path.write_bytes(original.encode("utf-8"))
        with self.assertRaisesRegex(StorageError, "accounts.csv, cabeçalho"):
            self.store.list(Account)
        with self.assertRaisesRegex(StorageError, "accounts.csv, cabeçalho"):
            self.store.create(Account("Conta", "cash"))
        self.assertEqual(path.read_bytes(), original.encode("utf-8"))

    def test_malformed_row_includes_record_number(self) -> None:
        path = self.directory / "categories.csv"
        path.write_text(
            "name,kind,active,id\nMercado,other,true,id-1\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(StorageError, "categories.csv, registro 2"):
            self.store.list(Category)

    def test_migrates_previous_transaction_schema_without_losing_records(self) -> None:
        account = self.store.create(Account("Conta", "bank"))
        category = self.store.create(Category("Mercado", "expense"))
        path = self.directory / "transactions.csv"
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["kind", "description", "amount", "date", "category_id",
                             "account_id", "notes", "id"])
            writer.writerow(["expense", "Feira", "25.50", "2026-10-01", category.id,
                             account.id, "", "legacy-transaction"])

        reopened = CsvStore(self.directory)
        migrated = reopened.get(Transaction, "legacy-transaction")
        self.assertEqual(migrated.description, "Feira")
        self.assertEqual(migrated.recurrence_id, "")
        self.assertIsNone(migrated.recurrence_date)


if __name__ == "__main__":
    unittest.main()
