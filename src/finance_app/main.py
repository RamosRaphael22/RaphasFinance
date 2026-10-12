"""Ponto de entrada do aplicativo."""

from finance_app.ui.app import FinanceApp


def main() -> None:
    """Abre a janela principal do aplicativo."""
    FinanceApp().mainloop()
