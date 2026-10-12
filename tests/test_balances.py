"""Cálculos de saldos, pagamentos de cartão e migração de contas."""

import csv
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance_app.domain.models import Account, Category, Transaction, Transfer
from finance_app.services import BalanceService
from finance_app.storage.csv_store import CsvStore, StorageError


class BalanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.directory = Path(self.temporary.name)
        self.store = CsvStore(self.directory)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_card_purchase_refund_and_payment_are_counted_once(self) -> None:
        bank = self.store.create(Account("Conta corrente", "bank", opening_balance=Decimal("1000.00")))
        card = self.store.create(Account("Cartão", "credit_card", opening_balance=Decimal("150.00")))
        expense_category = self.store.create(Category("Compras", "expense"))
        income_category = self.store.create(Category("Estorno", "income"))
        self.store.create(Transaction(
            "expense", "Compra no cartão", Decimal("250.00"), date(2026, 10, 1),
            expense_category.id, card.id,
        ))
        self.store.create(Transaction(
            "income", "Estorno no cartão", Decimal("20.00"), date(2026, 10, 2),
            income_category.id, card.id,
        ))
        payment = self.store.create(Transfer(
            bank.id, card.id, Decimal("100.00"), date(2026, 10, 3), "Pagamento da fatura",
        ))

        balances = {item.account.id: item.amount for item in BalanceService(self.store).list()}
        self.assertEqual(balances[bank.id], Decimal("900.00"))
        self.assertEqual(balances[card.id], Decimal("280.00"))
        self.assertEqual(len(self.store.list(Transaction)), 2)
        self.assertEqual(self.store.list(Transfer), [payment])

    def test_transfer_between_personal_accounts_moves_balance_without_income(self) -> None:
        cash = self.store.create(Account("Carteira", "cash", opening_balance=Decimal("75.00")))
        savings = self.store.create(Account("Poupança", "savings", opening_balance=Decimal("300.00")))
        self.store.create(Transfer(cash.id, savings.id, Decimal("25.00"), date(2026, 10, 4)))

        balances = {item.account.id: item.amount for item in BalanceService(self.store).list()}
        self.assertEqual(balances[cash.id], Decimal("50.00"))
        self.assertEqual(balances[savings.id], Decimal("325.00"))
        self.assertEqual(self.store.list(Transaction), [])

    def test_credit_card_cannot_be_transfer_source(self) -> None:
        card = self.store.create(Account("Cartão", "credit_card"))
        bank = self.store.create(Account("Banco", "bank"))
        with self.assertRaisesRegex(StorageError, "cartão não pode ser origem"):
            self.store.create(Transfer(card.id, bank.id, Decimal("10.00"), date.today()))
        self.assertEqual(self.store.list(Transfer), [])

    def test_transfer_preserves_account_references_and_blocks_account_deletion(self) -> None:
        source = self.store.create(Account("Conta de origem", "bank"))
        destination = self.store.create(Account("Conta de destino", "savings"))
        transfer = self.store.create(
            Transfer(source.id, destination.id, Decimal("10.00"), date(2026, 10, 4))
        )
        with self.assertRaisesRegex(StorageError, "conta em uso por transferências"):
            self.store.delete(Account, source.id)
        self.assertEqual(self.store.list(Transfer), [transfer])

    def test_migrates_previous_account_schema_without_losing_identifiers(self) -> None:
        account_path = self.directory / "accounts.csv"
        with account_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(["name", "kind", "active", "id"])
            writer.writerow(["Poupança", "savings", "true", "account-123"])

        migrated = CsvStore(self.directory).list(Account)
        self.assertEqual(len(migrated), 1)
        self.assertEqual(migrated[0].id, "account-123")
        self.assertEqual(migrated[0].opening_balance, Decimal("0"))
        with account_path.open(encoding="utf-8", newline="") as file:
            self.assertEqual(next(csv.reader(file)), [
                "name", "kind", "active", "id", "opening_balance",
            ])


if __name__ == "__main__":
    unittest.main()
