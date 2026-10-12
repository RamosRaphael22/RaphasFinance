"""Conversões de valores monetários para os campos em português do Brasil."""

from decimal import Decimal, InvalidOperation


def parse_brl_amount(value: str) -> Decimal:
    """Lê valores como 1234,56 ou 1.234,56 sem passar por float."""
    normalized = value.strip().replace("R$", "").replace(" ", "")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("Informe um valor válido, como 125,90.") from exc
    if not amount.is_finite():
        raise ValueError("O valor precisa ser finito.")
    return amount


def format_brl_amount(amount: Decimal) -> str:
    """Formata um Decimal em reais sem conversão binária ou arredondamento."""
    formatted = format(amount, ".2f")
    integer, fraction = formatted.lstrip("-").split(".")
    groups = []
    while integer:
        groups.append(integer[-3:])
        integer = integer[:-3]
    sign = "-" if amount < 0 else ""
    return f"{sign}R$ {'.'.join(reversed(groups))},{fraction}"
