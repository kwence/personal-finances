"""Expose the signed-in user's currency preference to every template."""

from .models import CURRENCY_CHOICES, CURRENCY_SYMBOLS, Profile


def currency(request):
    code = "USD"
    if getattr(request, "user", None) and request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        code = profile.currency

    return {
        "currency": code,
        "currency_symbol": CURRENCY_SYMBOLS.get(code, "$"),
        "currency_choices": [
            {
                "code": value,
                "label": label,
                "symbol": CURRENCY_SYMBOLS.get(value, "$"),
            }
            for value, label in CURRENCY_CHOICES
        ],
    }
