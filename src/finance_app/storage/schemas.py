"""Cabeçalhos e conversões centralizadas dos arquivos CSV."""

from dataclasses import fields
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Type

from finance_app.domain.models import (Account, Budget, Category, Goal, RecurrenceOccurrence,
                                       RecurrenceRule, Transaction, Transfer, Wish)

ENCODING = "utf-8"
DELIMITER = ","
LINE_TERMINATOR = "\n"


class SchemaError(ValueError):
    """Cabeçalho ou valor incompatível com o esquema CSV."""


class TableSpec:
    def __init__(self, filename: str, model: Type, columns: tuple[str, ...],
                 converters: dict[str, object] | None = None) -> None:
        self.filename = filename
        self.model = model
        self.columns = columns
        self.converters = converters or {}

    def parse(self, row: dict[str, str]):
        values = {}
        for column in self.columns:
            value = row[column]
            converter = self.converters.get(column)
            try:
                if converter is bool:
                    if value not in {"true", "false"}:
                        raise ValueError("esperado true ou false")
                    value = value == "true"
                elif converter:
                    value = converter(value)
            except (ValueError, InvalidOperation) as exc:
                raise SchemaError(f"coluna {column!r}: valor inválido {row[column]!r}") from exc
            values[column] = value
        return self.model(**values)

    def serialize(self, record) -> dict[str, str]:
        values = {}
        for column in self.columns:
            value = getattr(record, column)
            if isinstance(value, bool):
                values[column] = "true" if value else "false"
            elif isinstance(value, Decimal):
                values[column] = format(value, "f")
            elif isinstance(value, date):
                values[column] = value.isoformat()
            elif value is None:
                values[column] = ""
            else:
                values[column] = str(value)
        return values


TABLES = {
    Account: TableSpec("accounts.csv", Account,
                       tuple(field.name for field in fields(Account)),
                       {"active": bool, "opening_balance": Decimal}),
    Category: TableSpec("categories.csv", Category,
                        tuple(field.name for field in fields(Category)), {"active": bool}),
    Transaction: TableSpec(
        "transactions.csv", Transaction,
        tuple(field.name for field in fields(Transaction)),
        {"amount": Decimal, "date": date.fromisoformat,
         "recurrence_date": lambda value: date.fromisoformat(value) if value else None},
    ),
    Transfer: TableSpec(
        "transfers.csv", Transfer,
        tuple(field.name for field in fields(Transfer)),
        {"amount": Decimal, "date": date.fromisoformat},
    ),
    Wish: TableSpec("wishes.csv", Wish, tuple(field.name for field in fields(Wish)),
                    {"estimated_amount": Decimal, "saved_amount": Decimal,
                     "target_date": lambda value: date.fromisoformat(value) if value else None}),
    Goal: TableSpec("goals.csv", Goal, tuple(field.name for field in fields(Goal)),
                    {"target_amount": Decimal, "saved_amount": Decimal,
                     "deadline": lambda value: date.fromisoformat(value) if value else None}),
    Budget: TableSpec("budgets.csv", Budget, tuple(field.name for field in fields(Budget)),
                      {"limit_amount": Decimal}),
    RecurrenceRule: TableSpec(
        "recurrence_rules.csv", RecurrenceRule, tuple(field.name for field in fields(RecurrenceRule)),
        {"amount": Decimal, "interval": int, "start_date": date.fromisoformat,
         "end_date": lambda value: date.fromisoformat(value) if value else None, "active": bool},
    ),
    RecurrenceOccurrence: TableSpec(
        "recurrence_occurrences.csv", RecurrenceOccurrence,
        tuple(field.name for field in fields(RecurrenceOccurrence)),
        {"occurrence_date": date.fromisoformat},
    ),
}

LEGACY_ACCOUNT_COLUMNS = ("name", "kind", "active", "id")
LEGACY_ACCOUNT_SPEC = TableSpec("accounts.csv", Account, LEGACY_ACCOUNT_COLUMNS,
                                {"active": bool})
LEGACY_TRANSACTION_COLUMNS = ("kind", "description", "amount", "date", "category_id",
                              "account_id", "notes", "id")
LEGACY_TRANSACTION_SPEC = TableSpec(
    "transactions.csv", Transaction, LEGACY_TRANSACTION_COLUMNS,
    {"amount": Decimal, "date": date.fromisoformat},
)

