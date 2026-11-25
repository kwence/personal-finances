"""Small helpers shared by the dashboard and list views."""

from calendar import month_abbr
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum


def month_start(value=None):
    """First day of the given month (defaults to the current month)."""
    value = value or date.today()
    return date(value.year, value.month, 1)


def previous_month(value=None, steps=1):
    """First day of the month N months before ``value``."""
    current = month_start(value)
    index = current.year * 12 + current.month - 1 - steps
    return date(index // 12, index % 12 + 1, 1)


def month_label(year, month):
    return month_abbr[month]


def last_months(count=6, end=None):
    """Return ``[(year, month, label, start, end), ...]`` oldest first."""
    end = month_start(end)
    months = [previous_month(end, steps=steps) for steps in range(count - 1, -1, -1)]
    result = []
    for item in months:
        start = date(item.year, item.month, 1)
        finish = date(
            item.year + (item.month == 12), item.month % 12 + 1, 1
        )
        result.append((item.year, item.month, month_label(item.year, item.month), start, finish))
    return result


def totals(queryset):
    """Return (income, expense, balance) totals for a transaction queryset."""
    aggregates = queryset.aggregate(
        income=Sum("amount", filter=Q(category__type="income")),
        expense=Sum("amount", filter=Q(category__type="expense")),
    )
    income = aggregates["income"] or Decimal("0.00")
    expense = aggregates["expense"] or Decimal("0.00")
    return income, expense, income - expense


def parse_month(value):
    """Parse a ``YYYY-MM`` string into a date, or return None."""
    if not value:
        return None
    try:
        year, month = (int(part) for part in value.split("-"))
        return date(year, month, 1)
    except (ValueError, TypeError):
        return None
