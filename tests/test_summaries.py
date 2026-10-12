"""Cenários fictícios para o painel e os relatórios por período."""

import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance_app.domain.models import Account, Category, Transaction, Transfer
from finance_app.services import SummaryService
from finance_app.storage.csv_store import CsvStore


class SummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.store = CsvStore(Path(self.temporary.name))
        self.account = self.store.create(Account("Conta teste", "bank", opening_balance=Decimal("100")))
        self.market = self.store.create(Category("Mercado", "expense"))
        self.transport = self.store.create(Category("Transporte", "expense"))
        self.income = self.store.create(Category("Salário", "income"))
        self.service = SummaryService(self.store)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_period_totals_categories_months_and_end_balance(self) -> None:
        self.store.create(Transaction("income", "Anterior", Decimal("50"), date(2026, 1, 5), self.income.id, self.account.id))
        self.store.create(Transaction("income", "Pagamento", Decimal("200"), date(2026, 1, 20), self.income.id, self.account.id))
        self.store.create(Transaction("expense", "Feira", Decimal("80"), date(2026, 1, 21), self.market.id, self.account.id))
        self.store.create(Transaction("expense", "Ônibus", Decimal("20"), date(2026, 2, 2), self.transport.id, self.account.id))
        self.store.create(Transaction("expense", "Depois", Decimal("400"), date(2026, 2, 25), self.market.id, self.account.id))
        self.store.create(Transfer(self.account.id, self.store.create(Account("Poupança", "savings")).id,
                                  Decimal("10"), date(2026, 2, 10)))

        report = self.service.summarize(date(2026, 1, 15), date(2026, 2, 20))
        self.assertEqual(report.income, Decimal("200"))
        self.assertEqual(report.expenses, Decimal("100"))
        self.assertEqual(report.cash_flow, Decimal("100"))
        self.assertEqual([(item.name, item.amount) for item in report.category_expenses], [
            ("Mercado", Decimal("80")), ("Transporte", Decimal("20")),
        ])
        self.assertEqual([(item.month, item.income, item.expenses) for item in report.monthly_totals], [
            ("2026-01", Decimal("200"), Decimal("80")),
            ("2026-02", Decimal("0"), Decimal("20")),
        ])
        self.assertEqual(report.balances[0].amount, Decimal("240"))

    def test_rejects_reversed_period(self) -> None:
        with self.assertRaisesRegex(ValueError, "período válido"):
            self.service.summarize(date(2026, 2, 1), date(2026, 1, 1))

    def test_card_purchase_changes_cash_flow_only_when_invoice_is_paid(self) -> None:
        card = self.store.create(Account("Cartão", "credit_card"))
        purchase_date = date(2026, 10, 5)
        self.store.create(Transaction(
            "expense", "Compra no cartão", Decimal("100"), purchase_date,
            self.market.id, card.id,
        ))

        before_payment = self.service.summarize(purchase_date, purchase_date)
        self.assertEqual(before_payment.expenses, Decimal("100"))
        self.assertEqual(before_payment.cash_flow, Decimal("0"))
        before_balances = {item.account.id: item.amount for item in before_payment.balances}
        self.assertEqual(before_balances[self.account.id], Decimal("100"))
        self.assertEqual(before_balances[card.id], Decimal("100"))

        self.store.create(Transfer(
            self.account.id, card.id, Decimal("80"), purchase_date, "Pagamento parcial da fatura",
        ))
        after_payment = self.service.summarize(purchase_date, purchase_date)
        after_balances = {item.account.id: item.amount for item in after_payment.balances}
        self.assertEqual(after_payment.expenses, Decimal("100"))
        self.assertEqual(after_payment.cash_flow, Decimal("-80"))
        self.assertEqual(after_balances[self.account.id], Decimal("20"))
        self.assertEqual(after_balances[card.id], Decimal("20"))


if __name__ == "__main__":
    unittest.main()
