"""Operações de aplicação para cadastros pessoais."""

from __future__ import annotations

import calendar
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from finance_app.analytics.balances import AccountBalance, calculate_balances
from finance_app.analytics.summaries import FinancialSummary, summarize
from finance_app.analytics.forecasts import ForecastResult, forecast_monthly
from finance_app.domain.models import (Account, Budget, Category, Goal, RecurrenceOccurrence,
                                       RecurrenceRule, Transaction, Transfer, Wish)
from finance_app.storage.csv_store import CsvStore
from finance_app.storage.portability import CsvPortability


class CatalogService:
    """Coordena consultas e alterações em contas e categorias."""

    def __init__(self, store: CsvStore) -> None:
        self.store = store

    def list(self, model: type[Account] | type[Category]) -> list[Account] | list[Category]:
        return self.store.list(model)

    def save(self, record: Account | Category) -> Account | Category:
        if self.store.get(type(record), record.id) is None:
            return self.store.create(record)
        return self.store.update(record)

    def set_active(self, record: Account | Category, active: bool) -> Account | Category:
        updated = replace(record, active=active)
        return self.store.update(updated)

    def delete(self, record: Account | Category) -> None:
        self.store.delete(type(record), record.id)


class TransactionService:
    """Aplica filtros e regras de cadastro de receitas e despesas."""

    def __init__(self, store: CsvStore) -> None:
        self.store = store

    def list(
        self,
        *,
        query: str = "",
        start: date | None = None,
        end: date | None = None,
        kind: str | None = None,
        category_id: str | None = None,
        account_id: str | None = None,
    ) -> list[Transaction]:
        if start and end and start > end:
            raise ValueError("A data inicial deve ser anterior ou igual à data final.")
        search = query.strip().casefold()
        records = self.store.list(Transaction)
        if search:
            records = [item for item in records if search in item.description.casefold()
                       or search in item.notes.casefold()]
        if start:
            records = [item for item in records if item.date >= start]
        if end:
            records = [item for item in records if item.date <= end]
        if kind:
            records = [item for item in records if item.kind == kind]
        if category_id:
            records = [item for item in records if item.category_id == category_id]
        if account_id:
            records = [item for item in records if item.account_id == account_id]
        return sorted(records, key=lambda item: (item.date, item.id), reverse=True)

    def save(self, record: Transaction) -> Transaction:
        existing = self.store.get(Transaction, record.id)
        account = self.store.get(Account, record.account_id)
        category = self.store.get(Category, record.category_id)
        if account is None or category is None:
            raise ValueError("Selecione uma conta e uma categoria existentes.")
        if not account.active and (existing is None or existing.account_id != account.id):
            raise ValueError("Selecione uma conta ativa para o lançamento.")
        if not category.active and (existing is None or existing.category_id != category.id):
            raise ValueError("Selecione uma categoria ativa para o lançamento.")
        if category.kind != record.kind:
            raise ValueError("O tipo de lançamento deve corresponder ao tipo da categoria.")
        return self.store.create(record) if existing is None else self.store.update(record)

    def delete(self, record_id: str) -> None:
        self.store.delete(Transaction, record_id)


class TransferService:
    """Coordena transferências entre contas pessoais e pagamentos de cartão."""

    def __init__(self, store: CsvStore) -> None:
        self.store = store

    def list(self) -> list[Transfer]:
        return sorted(self.store.list(Transfer), key=lambda item: (item.date, item.id), reverse=True)

    def save(self, record: Transfer) -> Transfer:
        existing = self.store.get(Transfer, record.id)
        source = self.store.get(Account, record.source_account_id)
        destination = self.store.get(Account, record.destination_account_id)
        if source is None or destination is None:
            raise ValueError("Selecione contas existentes para a origem e o destino.")
        if source.kind == "credit_card":
            raise ValueError("Um cartão de crédito não pode ser a origem da transferência.")
        if not source.active and (existing is None or existing.source_account_id != source.id):
            raise ValueError("Selecione uma conta de origem ativa.")
        if not destination.active and (
            existing is None or existing.destination_account_id != destination.id
        ):
            raise ValueError("Selecione uma conta de destino ativa.")
        return self.store.create(record) if existing is None else self.store.update(record)

    def delete(self, record_id: str) -> None:
        self.store.delete(Transfer, record_id)


class BalanceService:
    """Fornece saldos calculados a partir de contas, lançamentos e transferências."""

    def __init__(self, store: CsvStore) -> None:
        self.store = store

    def list(self) -> list[AccountBalance]:
        return calculate_balances(
            self.store.list(Account),
            self.store.list(Transaction),
            self.store.list(Transfer),
        )


class SummaryService:
    """Monta relatórios a partir das tabelas atuais, sem persistir valores derivados."""

    def __init__(self, store: CsvStore) -> None:
        self.store = store

    def summarize(self, start: date, end: date) -> FinancialSummary:
        return summarize(
            start, end, self.store.list(Transaction), self.store.list(Category),
            self.store.list(Account), self.store.list(Transfer),
        )


class ForecastService:
    """Calcula uma projeção simples sem gravá-la nos registros realizados."""

    def __init__(self, store: CsvStore) -> None:
        self.store = store

    def forecast(self, *, as_of: date | None = None, months_ahead: int = 3) -> ForecastResult:
        return forecast_monthly(self.store.list(Transaction), as_of=as_of,
                                months_ahead=months_ahead)


class PortabilityService:
    """Expose backup, restore, and export operations to the application layer."""

    def __init__(self, store: CsvStore) -> None:
        self.csv = CsvPortability(store.directory)

    def backup(self, destination: Path | str) -> Path:
        return self.csv.create_backup(destination)

    def restore(self, source: Path | str) -> None:
        self.csv.restore_backup(source)

    def export(self, destination: Path | str) -> Path:
        return self.csv.export_csv(destination)


class PlanningService:
    """Desejos, metas e limites mensais acompanhados a partir dos lançamentos."""

    def __init__(self, store: CsvStore) -> None:
        self.store = store

    def list(self, model: type[Wish] | type[Goal] | type[Budget]):
        return self.store.list(model)

    def save(self, record: Wish | Goal | Budget):
        existing = self.store.get(type(record), record.id)
        if isinstance(record, Budget):
            category = self.store.get(Category, record.category_id)
            if category is None or category.kind != "expense":
                raise ValueError("Orçamentos precisam usar uma categoria de despesa.")
            if not category.active and (existing is None or existing.category_id != category.id):
                raise ValueError("Selecione uma categoria de despesa ativa.")
            duplicate = next((item for item in self.store.list(Budget)
                              if item.category_id == record.category_id
                              and item.period == record.period and item.id != record.id), None)
            if duplicate:
                raise ValueError("Já existe um orçamento para essa categoria e mês.")
        return self.store.create(record) if existing is None else self.store.update(record)

    def delete(self, model: type[Wish] | type[Goal] | type[Budget], record_id: str) -> None:
        self.store.delete(model, record_id)

    def budget_spending(self, budget: Budget):
        transactions = self.store.list(Transaction)
        return sum((item.amount for item in transactions
                    if item.kind == "expense" and item.category_id == budget.category_id
                    and item.date.strftime("%Y-%m") == budget.period), Decimal("0"))


class RecurrenceService:
    """Regras recorrentes com confirmação manual e proteção contra duplicatas."""

    def __init__(self, store: CsvStore) -> None:
        self.store = store

    def list(self) -> list[RecurrenceRule]:
        return sorted(self.store.list(RecurrenceRule), key=lambda item: (item.active is False, item.name.casefold()))

    def save(self, rule: RecurrenceRule) -> RecurrenceRule:
        existing = self.store.get(RecurrenceRule, rule.id)
        category = self.store.get(Category, rule.category_id)
        account = self.store.get(Account, rule.account_id)
        if category is None or account is None or category.kind != rule.kind:
            raise ValueError("Selecione uma categoria compatível e uma conta existentes.")
        if not category.active and (existing is None or existing.category_id != category.id):
            raise ValueError("Selecione uma categoria ativa.")
        if not account.active and (existing is None or existing.account_id != account.id):
            raise ValueError("Selecione uma conta ativa.")
        return self.store.create(rule) if existing is None else self.store.update(rule)

    def set_active(self, rule: RecurrenceRule, active: bool) -> RecurrenceRule:
        return self.store.update(replace(rule, active=active))

    def delete(self, rule_id: str) -> None:
        self.store.delete(RecurrenceRule, rule_id)

    def pending(self, today: date | None = None) -> list[tuple[RecurrenceRule, date]]:
        today = today or date.today()
        processed = {(item.rule_id, item.occurrence_date)
                     for item in self.store.list(RecurrenceOccurrence)}
        transactions = {(item.recurrence_id, item.recurrence_date)
                        for item in self.store.list(Transaction) if item.recurrence_id}
        pending = []
        for rule in self.list():
            if not rule.active:
                continue
            occurrence = rule.start_date
            index = 0
            while occurrence <= today and (rule.end_date is None or occurrence <= rule.end_date):
                key = (rule.id, occurrence)
                if key not in processed and key not in transactions:
                    pending.append((rule, occurrence))
                index += 1
                occurrence = self._occurrence_date(rule, index)
                if index > 20000:
                    break
        return sorted(pending, key=lambda item: (item[1], item[0].name.casefold()))

    def confirm(self, rule_id: str, occurrence_date: date) -> Transaction:
        rule = self.store.get(RecurrenceRule, rule_id)
        if rule is None or not rule.active:
            raise ValueError("A regra não existe ou está desativada.")
        if (rule, occurrence_date) not in self.pending():
            raise ValueError("A ocorrência não está vencida ou já foi processada.")
        key = (rule_id, occurrence_date)
        known = next((item for item in self.store.list(RecurrenceOccurrence)
                      if (item.rule_id, item.occurrence_date) == key), None)
        if known:
            raise ValueError("Esta ocorrência já foi processada.")
        transaction = next((item for item in self.store.list(Transaction)
                            if (item.recurrence_id, item.recurrence_date) == key), None)
        if transaction is None:
            transaction = Transaction(
                kind=rule.kind, description=rule.description, amount=rule.amount,
                date=occurrence_date, category_id=rule.category_id,
                account_id=rule.account_id, recurrence_id=rule.id,
                recurrence_date=occurrence_date,
            )
            self.store.create(transaction)
        self.store.create(RecurrenceOccurrence(rule.id, occurrence_date, "confirmed"))
        return transaction

    def skip(self, rule_id: str, occurrence_date: date) -> RecurrenceOccurrence:
        rule = self.store.get(RecurrenceRule, rule_id)
        if rule is None:
            raise ValueError("A regra de recorrência não existe.")
        if (rule, occurrence_date) not in self.pending():
            raise ValueError("A ocorrência não está vencida ou já foi processada.")
        key = (rule_id, occurrence_date)
        if any((item.rule_id, item.occurrence_date) == key
               for item in self.store.list(RecurrenceOccurrence)):
            raise ValueError("Esta ocorrência já foi processada.")
        if any((item.recurrence_id, item.recurrence_date) == key
               for item in self.store.list(Transaction)):
            raise ValueError("Esta ocorrência já gerou um lançamento.")
        return self.store.create(RecurrenceOccurrence(rule.id, occurrence_date, "skipped"))

    @staticmethod
    def _occurrence_date(rule: RecurrenceRule, index: int) -> date:
        if rule.frequency == "weekly":
            return rule.start_date + timedelta(days=7 * rule.interval * index)
        if rule.frequency == "monthly":
            month_index = rule.start_date.year * 12 + rule.start_date.month - 1 + rule.interval * index
            year, month0 = divmod(month_index, 12)
            month = month0 + 1
            day = min(rule.start_date.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)
        year = rule.start_date.year + rule.interval * index
        day = min(rule.start_date.day, calendar.monthrange(year, rule.start_date.month)[1])
        return date(year, rule.start_date.month, day)
