"""Testes das previsões explicáveis com lançamentos exclusivamente fictícios."""

import unittest
from datetime import date
from decimal import Decimal

from finance_app.domain.models import Transaction
from finance_app.analytics.forecasts import forecast_monthly


def transaction(kind: str, amount: str, year: int, month: int, day: int = 15) -> Transaction:
    return Transaction(kind, "Lançamento fictício", Decimal(amount), date(year, month, day),
                       "category-id", "account-id")


class ForecastTests(unittest.TestCase):
    def test_uses_six_complete_months_and_excludes_current_partial_month(self) -> None:
        records = []
        for month in (4, 5, 6, 7, 9):
            records.append(transaction("income", "120.00", 2026, month))
            records.append(transaction("expense", "60.00", 2026, month))
        records.append(transaction("income", "9000.00", 2026, 10))

        result = forecast_monthly(records, as_of=date(2026, 10, 11), months_ahead=3)
        self.assertTrue(result.available)
        self.assertEqual(result.history_start, date(2026, 4, 1))
        self.assertEqual(result.history_end, date(2026, 9, 30))
        self.assertEqual(result.months_with_activity, 5)
        self.assertEqual([item.month for item in result.forecasts], ["2026-11", "2026-12", "2027-01"])
        self.assertEqual(result.forecasts[0].income, Decimal("100.00"))
        self.assertEqual(result.forecasts[0].expenses, Decimal("50.00"))
        self.assertEqual(result.forecasts[0].result, Decimal("50.00"))

    def test_refuses_short_history_and_sparse_activity(self) -> None:
        short = forecast_monthly(
            [transaction("income", "100", 2026, 7)], as_of=date(2026, 10, 11),
        )
        self.assertFalse(short.available)
        self.assertIn("não cobre", short.reason)

        sparse = [transaction("income", "100", 2026, month) for month in (4, 5, 6)]
        result = forecast_monthly(sparse, as_of=date(2026, 10, 11))
        self.assertFalse(result.available)
        self.assertIn("apenas 3", result.reason)

    def test_rejects_invalid_horizon(self) -> None:
        with self.assertRaisesRegex(ValueError, "1 a 12"):
            forecast_monthly([], as_of=date(2026, 10, 11), months_ahead=13)


if __name__ == "__main__":
    unittest.main()
