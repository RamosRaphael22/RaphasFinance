"""Testes da persistência das datas escolhidas no painel."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from finance_app.storage.dashboard_preferences import DashboardPeriodPreferences


class DashboardPeriodPreferencesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.path = Path(self.temporary.name) / "settings" / "dashboard_period.json"
        self.preferences = DashboardPeriodPreferences(self.path)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_load_returns_none_until_a_period_is_saved(self) -> None:
        self.assertIsNone(self.preferences.load())

    def test_save_and_load_preserve_selected_dates(self) -> None:
        selected = (date(2025, 11, 1), date(2026, 10, 11))

        self.preferences.save(*selected)

        self.assertEqual(self.preferences.load(), selected)

    def test_invalid_period_is_not_saved(self) -> None:
        with self.assertRaisesRegex(ValueError, "período válido"):
            self.preferences.save(date(2026, 10, 11), date(2025, 11, 1))
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
