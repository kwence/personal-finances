"""Template tag that formats money using the user's chosen currency."""

from decimal import Decimal, InvalidOperation

from django.template import Library

from finances.models import CURRENCY_SYMBOLS

register = Library()


@register.simple_tag(takes_context=True)
def money(context, value):
    """Render an amount as e.g. £1,250.50 / $1,250.50 / €1,250.50."""
    code = context.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(code, "$")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0.00")

    sign = "-" if amount < 0 else ""
    return f"{sign}{symbol}{abs(amount):,.2f}"
