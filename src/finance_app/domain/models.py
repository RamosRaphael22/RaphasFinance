"""Entidades pessoais usadas pelo domínio e pela persistência."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import uuid4


@dataclass(frozen=True)
class Account:
    name: str
    kind: str
    active: bool = True
    id: str = field(default_factory=lambda: str(uuid4()))
    opening_balance: Decimal = Decimal("0")


@dataclass(frozen=True)
class Category:
    name: str
    kind: str
    active: bool = True
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class Transaction:
    kind: str
    description: str
    amount: Decimal
    date: date
    category_id: str
    account_id: str
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    recurrence_id: str = ""
    recurrence_date: date | None = None


@dataclass(frozen=True)
class Transfer:
    source_account_id: str
    destination_account_id: str
    amount: Decimal
    date: date
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class Wish:
    name: str
    estimated_amount: Decimal
    saved_amount: Decimal = Decimal("0")
    priority: str = "medium"
    status: str = "planned"
    target_date: date | None = None
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class Goal:
    name: str
    target_amount: Decimal
    saved_amount: Decimal = Decimal("0")
    deadline: date | None = None
    priority: str = "medium"
    status: str = "active"
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class Budget:
    category_id: str
    period: str
    limit_amount: Decimal
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class RecurrenceRule:
    name: str
    kind: str
    description: str
    amount: Decimal
    category_id: str
    account_id: str
    frequency: str
    interval: int
    start_date: date
    end_date: date | None = None
    active: bool = True
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class RecurrenceOccurrence:
    rule_id: str
    occurrence_date: date
    status: str
    id: str = field(default_factory=lambda: str(uuid4()))
