"""Cálculo de saldos atuais por conta pessoal."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finance_app.domain.models import Account, Transaction, Transfer


@dataclass(frozen=True)
class AccountBalance:
    account: Account
    amount: Decimal


def calculate_balances(
    accounts: list[Account],
    transactions: list[Transaction],
    transfers: list[Transfer],
    through: date | None = None,
) -> list[AccountBalance]:
    """Calcula saldos desde o saldo inicial de cada conta."""
    balances = []
    for account in accounts:
        amount = account.opening_balance
        is_card = account.kind == "credit_card"
        for entry in transactions:
            if entry.account_id != account.id:
                continue
            if through is not None and entry.date > through:
                continue
            if is_card:
                amount += entry.amount if entry.kind == "expense" else -entry.amount
            else:
                amount += entry.amount if entry.kind == "income" else -entry.amount
        for transfer in transfers:
            if through is not None and transfer.date > through:
                continue
            if transfer.source_account_id == account.id:
                amount -= transfer.amount
            if transfer.destination_account_id == account.id:
                amount -= transfer.amount if is_card else -transfer.amount
        balances.append(AccountBalance(account, amount))
    return balances
