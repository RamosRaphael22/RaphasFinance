"""Previsão mensal simples, limitada e separada dos valores realizados."""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from finance_app.domain.models import Transaction

CENT = Decimal("0.01")


@dataclass(frozen=True)
class ForecastMonth:
    month: str
    income: Decimal
    expenses: Decimal
    result: Decimal


@dataclass(frozen=True)
class ForecastResult:
    available: bool
    reason: str
    history_start: date
    history_end: date
    history_months: int
    months_with_activity: int
    forecasts: list[ForecastMonth]


def forecast_monthly(
    transactions: list[Transaction],
    *,
    as_of: date | None = None,
    history_months: int = 6,
    months_ahead: int = 3,
) -> ForecastResult:
    """Projeta médias mensais se houver seis meses completos e atividade em quatro.

    O mês corrente fica fora do histórico por estar incompleto. Meses sem
    lançamentos dentro da janela contam como zero na média.
    """
    as_of = as_of or date.today()
    if type(as_of) is not date:
        raise ValueError("A data de referência deve ser válida.")
    if history_months != 6:
        raise ValueError("A janela de histórico deve conter seis meses completos.")
    if type(months_ahead) is not int or not 1 <= months_ahead <= 12:
        raise ValueError("O horizonte deve ter de 1 a 12 meses.")

    last_month_index = as_of.year * 12 + as_of.month - 2
    last_year, last_month_zero = divmod(last_month_index, 12)
    last_month = last_month_zero + 1
    first_index = last_year * 12 + last_month - history_months
    first_year, first_month_zero = divmod(first_index, 12)
    first_month = first_month_zero + 1
    history_start = date(first_year, first_month, 1)
    history_end = date(last_year, last_month, calendar.monthrange(last_year, last_month)[1])

    if not transactions:
        return ForecastResult(False, "Ainda não há lançamentos para formar um histórico.",
                              history_start, history_end, history_months, 0, [])
    earliest = min(item.date for item in transactions)
    if earliest.strftime("%Y-%m") > history_start.strftime("%Y-%m"):
        return ForecastResult(
            False,
            f"O histórico ainda não cobre os seis meses completos necessários. "
            f"Há lançamentos a partir de {earliest.strftime('%d/%m/%Y')}.",
            history_start, history_end, history_months, 0, [],
        )

    buckets = {f"{year:04d}-{month:02d}": [Decimal("0"), Decimal("0")]
               for year, month in _month_sequence(first_year, first_month, history_months)}
    for item in transactions:
        key = item.date.strftime("%Y-%m")
        if key in buckets:
            buckets[key][0 if item.kind == "income" else 1] += item.amount
    months_with_activity = sum(any(values) for values in buckets.values())
    if months_with_activity < 4:
        return ForecastResult(
            False,
            f"A janela cobre seis meses, mas houve lançamentos em apenas "
            f"{months_with_activity}; são necessários ao menos quatro meses ativos.",
            history_start, history_end, history_months, months_with_activity, [],
        )

    income_average = (sum((values[0] for values in buckets.values()), Decimal("0"))
                      / history_months).quantize(CENT, rounding=ROUND_HALF_UP)
    expense_average = (sum((values[1] for values in buckets.values()), Decimal("0"))
                       / history_months).quantize(CENT, rounding=ROUND_HALF_UP)
    forecasts = []
    year, month = as_of.year, as_of.month + 1
    if month == 13:
        year += 1; month = 1
    for _ in range(months_ahead):
        forecasts.append(ForecastMonth(
            f"{year:04d}-{month:02d}", income_average, expense_average,
            income_average - expense_average,
        ))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return ForecastResult(True, "", history_start, history_end, history_months,
                          months_with_activity, forecasts)


def _month_sequence(year: int, month: int, count: int):
    for _ in range(count):
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
