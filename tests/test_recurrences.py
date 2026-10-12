"""Datas fictícias para calendário e processamento idempotente de recorrências."""

import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance_app.domain.models import (Account, Category, RecurrenceOccurrence,
                                       RecurrenceRule, Transaction)
from finance_app.services import RecurrenceService
from finance_app.storage.csv_store import CsvStore, StorageError


class RecurrenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.store = CsvStore(Path(self.temporary.name))
        account = self.store.create(Account("Conta fictícia", "bank"))
        category = self.store.create(Category("Conta fictícia", "expense"))
        self.service = RecurrenceService(self.store)
        self.rule = self.service.save(RecurrenceRule(
            name="Aluguel fictício", kind="expense", description="Aluguel",
            amount=Decimal("1000"), category_id=category.id, account_id=account.id,
            frequency="monthly", interval=1, start_date=date(2025, 1, 31),
        ))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_month_end_clamps_short_month_and_keeps_anchor_day(self) -> None:
        pending = self.service.pending(date(2025, 3, 31))
        self.assertEqual([due for _, due in pending], [
            date(2025, 1, 31), date(2025, 2, 28), date(2025, 3, 31),
        ])

    def test_confirm_and_skip_are_idempotent_after_reprocessing(self) -> None:
        due = date(2025, 2, 28)
        self.service.confirm(self.rule.id, due)
        self.assertNotIn((self.rule, due), self.service.pending(date(2025, 3, 31)))
        self.assertEqual(len(self.store.list(Transaction)), 1)
        with self.assertRaisesRegex(ValueError, "já foi processada"):
            self.service.confirm(self.rule.id, due)
        self.service.skip(self.rule.id, date(2025, 1, 31))
        self.assertNotIn((self.rule, date(2025, 1, 31)), self.service.pending(date(2025, 3, 31)))
        self.assertEqual(len(self.store.list(Transaction)), 1)

    def test_generated_occurrence_cannot_be_duplicated_in_storage(self) -> None:
        due = date(2025, 1, 31)
        transaction = self.service.confirm(self.rule.id, due)
        duplicate = Transaction(
            transaction.kind, transaction.description, transaction.amount,
            transaction.date, transaction.category_id, transaction.account_id,
            recurrence_id=self.rule.id, recurrence_date=due,
        )
        with self.assertRaisesRegex(StorageError, "duplicada"):
            self.store.create(duplicate)

    def test_processed_occurrence_key_is_unique(self) -> None:
        occurrence_date = date(2025, 1, 31)
        self.store.create(RecurrenceOccurrence(self.rule.id, occurrence_date, "skipped"))
        with self.assertRaisesRegex(StorageError, "ocorrência duplicada"):
            self.store.create(RecurrenceOccurrence(self.rule.id, occurrence_date, "skipped"))

    def test_delete_rule_keeps_confirmed_transaction_and_removes_rule_history(self) -> None:
        due = date(2025, 1, 31)
        transaction = self.service.confirm(self.rule.id, due)
        skipped_due = date(2025, 2, 28)
        self.service.skip(self.rule.id, skipped_due)

        self.service.delete(self.rule.id)

        self.assertEqual(self.service.list(), [])
        preserved = self.store.get(Transaction, transaction.id)
        self.assertEqual(preserved.description, transaction.description)
        self.assertEqual(preserved.amount, transaction.amount)
        self.assertEqual(preserved.date, due)
        self.assertEqual(preserved.recurrence_id, "")
        self.assertIsNone(preserved.recurrence_date)
        self.assertEqual(self.store.list(RecurrenceOccurrence), [])


if __name__ == "__main__":
    unittest.main()
