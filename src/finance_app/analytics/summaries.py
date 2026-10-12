"""Resumos realizados para um intervalo selecionado pelo usuário."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finance_app.analytics.balances import AccountBalance, calculate_balances
from finance_app.domain.models import Account, Category, Transaction, Transfer


@dataclass(frozen=True)
class CategoryTotal:
    name: str
    amount: Decimal


@dataclass(frozen=True)
class MonthlyTotal:
    month: str
    income: Decimal
    expenses: Decimal


@dataclass(frozen=True)
class FinancialSummary:
    start: date
    end: date
    income: Decimal
    expenses: Decimal
    cash_flow: Decimal
    balances: list[AccountBalance]
    category_expenses: list[CategoryTotal]
    monthly_totals: list[MonthlyTotal]


def summarize(
    start: date,
    end: date,
    transactions: list[Transaction],
    categories: list[Category],
    accounts: list[Account],
    transfers: list[Transfer],
) -> FinancialSummary:
    """Calcula totais do período e fluxo de caixa, com saldos até a data final."""
    if type(start) is not date or type(end) is not date or start > end:
        raise ValueError("Informe um período válido, com início anterior ou igual ao fim.")
    selected = [item for item in transactions if start <= item.date <= end]
    income = sum((item.amount for item in selected if item.kind == "income"), Decimal("0"))
    expenses = sum((item.amount for item in selected if item.kind == "expense"), Decimal("0"))
    accounts_by_id = {item.id: item for item in accounts}
    cash_flow = sum((
        item.amount if item.kind == "income" else -item.amount
        for item in selected
        if accounts_by_id.get(item.account_id) is not None
        and accounts_by_id[item.account_id].kind != "credit_card"
    ), Decimal("0"))
    cash_flow -= sum((
        item.amount for item in transfers
        if start <= item.date <= end
        and accounts_by_id.get(item.destination_account_id) is not None
        and accounts_by_id[item.destination_account_id].kind == "credit_card"
    ), Decimal("0"))
    category_names = {item.id: item.name for item in categories}
    totals: dict[str, Decimal] = {}
    for item in selected:
        if item.kind == "expense":
            totals[item.category_id] = totals.get(item.category_id, Decimal("0")) + item.amount
    category_expenses = sorted(
        (CategoryTotal(category_names.get(category_id, "Categoria indisponível"), amount)
         for category_id, amount in totals.items()),
        key=lambda item: (-item.amount, item.name.casefold()),
    )

    monthly: dict[str, list[Decimal]] = {}
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        monthly[f"{year:04d}-{month:02d}"] = [Decimal("0"), Decimal("0")]
        next_month = month + 1
        year, month = (year + 1, 1) if next_month == 13 else (year, next_month)
    for item in selected:
        bucket = monthly[item.date.strftime("%Y-%m")]
        bucket[0 if item.kind == "income" else 1] += item.amount
    monthly_totals = [MonthlyTotal(month, values[0], values[1])
                      for month, values in monthly.items()]
    balances = calculate_balances(accounts, transactions, transfers, through=end)
    return FinancialSummary(
        start, end, income, expenses, cash_flow, balances,
        category_expenses, monthly_totals,
    )
