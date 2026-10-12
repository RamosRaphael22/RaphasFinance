"""Validações de registros antes de persistir dados pessoais."""

from datetime import date
from decimal import Decimal, InvalidOperation

from finance_app.domain.models import (Account, Budget, Category, Goal, RecurrenceOccurrence,
                                       RecurrenceRule, Transaction, Transfer, Wish)

ACCOUNT_KINDS = {"cash", "bank", "savings", "credit_card"}
TRANSACTION_KINDS = {"income", "expense"}
PRIORITIES = {"low", "medium", "high"}


class ValidationError(ValueError):
    """Registro inválido para as regras do aplicativo."""


def validate(record: Account | Category | Transaction | Transfer | Wish | Goal | Budget |
             RecurrenceRule | RecurrenceOccurrence) -> None:
    if not isinstance(record.id, str) or not record.id.strip():
        raise ValidationError("O identificador não pode ficar vazio.")

    if isinstance(record, Account):
        _required(record.name, "O nome da conta")
        if not isinstance(record.active, bool):
            raise ValidationError("A situação da conta deve ser true ou false.")
        if not isinstance(record.kind, str) or record.kind not in ACCOUNT_KINDS:
            raise ValidationError(f"Tipo de conta inválido: {record.kind!r}.")
        _validate_amount(
            record.opening_balance,
            "O saldo inicial",
            allow_negative=record.kind != "credit_card",
        )
    elif isinstance(record, Category):
        _required(record.name, "O nome da categoria")
        if not isinstance(record.active, bool):
            raise ValidationError("A situação da categoria deve ser true ou false.")
        if not isinstance(record.kind, str) or record.kind not in TRANSACTION_KINDS:
            raise ValidationError(f"Tipo de categoria inválido: {record.kind!r}.")
    elif isinstance(record, Transaction):
        _required(record.description, "A descrição")
        if not isinstance(record.kind, str) or record.kind not in TRANSACTION_KINDS:
            raise ValidationError(f"Tipo de lançamento inválido: {record.kind!r}.")
        _validate_amount(record.amount, "O valor", allow_zero=False, allow_negative=False)
        if type(record.date) is not date:
            raise ValidationError("A data deve ser uma data válida.")
        if not isinstance(record.category_id, str) or not record.category_id.strip():
            raise ValidationError("Lançamentos precisam de conta e categoria.")
        if not isinstance(record.account_id, str) or not record.account_id.strip():
            raise ValidationError("Lançamentos precisam de conta e categoria.")
        if not isinstance(record.notes, str):
            raise ValidationError("A observação deve ser um texto.")
        if not isinstance(record.recurrence_id, str):
            raise ValidationError("A referência da recorrência deve ser um texto.")
        if bool(record.recurrence_id) != (record.recurrence_date is not None):
            raise ValidationError("A referência da recorrência está incompleta.")
        if record.recurrence_date is not None and type(record.recurrence_date) is not date:
            raise ValidationError("A data da ocorrência recorrente deve ser válida.")
    elif isinstance(record, Transfer):
        _validate_amount(record.amount, "O valor da transferência", allow_zero=False,
                         allow_negative=False)
        if type(record.date) is not date:
            raise ValidationError("A data da transferência deve ser uma data válida.")
        if not isinstance(record.source_account_id, str) or not record.source_account_id.strip():
            raise ValidationError("Selecione a conta de origem.")
        if not isinstance(record.destination_account_id, str) or not record.destination_account_id.strip():
            raise ValidationError("Selecione a conta de destino.")
        if record.source_account_id == record.destination_account_id:
            raise ValidationError("A origem e o destino precisam ser contas diferentes.")
        if not isinstance(record.notes, str):
            raise ValidationError("A observação da transferência deve ser um texto.")
    elif isinstance(record, Wish):
        _required(record.name, "O nome do desejo")
        _validate_amount(record.estimated_amount, "O valor estimado", allow_zero=False, allow_negative=False)
        _validate_amount(record.saved_amount, "O valor reservado", allow_negative=False)
        if record.priority not in PRIORITIES or record.status not in {"planned", "purchased", "cancelled"}:
            raise ValidationError("Prioridade ou situação do desejo inválida.")
        if record.target_date is not None and type(record.target_date) is not date:
            raise ValidationError("A data desejada deve ser válida.")
    elif isinstance(record, Goal):
        _required(record.name, "O nome da meta")
        _validate_amount(record.target_amount, "O valor da meta", allow_zero=False, allow_negative=False)
        _validate_amount(record.saved_amount, "O valor acumulado", allow_negative=False)
        if record.priority not in PRIORITIES or record.status not in {"active", "completed", "paused"}:
            raise ValidationError("Prioridade ou situação da meta inválida.")
        if record.deadline is not None and type(record.deadline) is not date:
            raise ValidationError("O prazo da meta deve ser válido.")
    elif isinstance(record, Budget):
        _validate_amount(record.limit_amount, "O limite do orçamento", allow_zero=False, allow_negative=False)
        if not isinstance(record.category_id, str) or not record.category_id.strip():
            raise ValidationError("Selecione uma categoria de despesa.")
        if not isinstance(record.period, str) or len(record.period) != 7 or record.period[4] != "-":
            raise ValidationError("O período deve usar o formato AAAA-MM.")
        try:
            year, month = map(int, record.period.split("-"))
            if year < 1 or not 1 <= month <= 12:
                raise ValueError
        except ValueError as exc:
            raise ValidationError("O período deve usar o formato AAAA-MM.") from exc
    elif isinstance(record, RecurrenceRule):
        _required(record.name, "O nome da recorrência")
        _required(record.description, "A descrição")
        _validate_amount(record.amount, "O valor", allow_zero=False, allow_negative=False)
        if record.kind not in TRANSACTION_KINDS:
            raise ValidationError("Tipo de recorrência inválido.")
        if record.frequency not in {"weekly", "monthly", "yearly"}:
            raise ValidationError("A frequência deve ser semanal, mensal ou anual.")
        if type(record.interval) is not int or record.interval < 1 or record.interval > 60:
            raise ValidationError("O intervalo deve ser um número inteiro entre 1 e 60.")
        if type(record.start_date) is not date:
            raise ValidationError("A data inicial deve ser válida.")
        if record.end_date is not None and (type(record.end_date) is not date or record.end_date < record.start_date):
            raise ValidationError("A data final deve ser válida e posterior à inicial.")
        if not isinstance(record.active, bool):
            raise ValidationError("A situação da recorrência deve ser true ou false.")
        _required(record.category_id, "A categoria")
        _required(record.account_id, "A conta")
    elif isinstance(record, RecurrenceOccurrence):
        _required(record.rule_id, "A regra de recorrência")
        if type(record.occurrence_date) is not date:
            raise ValidationError("A data da ocorrência deve ser válida.")
        if record.status not in {"confirmed", "skipped"}:
            raise ValidationError("A situação da ocorrência deve ser confirmada ou ignorada.")


def _required(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} não pode ficar vazio.")


def _validate_amount(value: Decimal, label: str, *, allow_zero: bool = True,
                     allow_negative: bool = True) -> None:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{label} deve usar Decimal, sem conversão de float.")
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(f"{label} deve ser um decimal válido.") from exc
    if not amount.is_finite():
        raise ValidationError(f"{label} deve ser finito.")
    if not allow_zero and amount == 0:
        raise ValidationError(f"{label} deve ser diferente de zero.")
    if not allow_negative and amount < 0:
        raise ValidationError(f"{label} não pode ser negativo.")
    if amount.normalize().as_tuple().exponent < -2:
        raise ValidationError(f"{label} pode ter no máximo duas casas decimais.")
