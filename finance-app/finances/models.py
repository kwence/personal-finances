"""Database models for the personal finance app.

Every record belongs to a user, so one account can never see another
account's money data.
"""

from datetime import date

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

TYPE_CHOICES = (
    ("income", "Income"),
    ("expense", "Expense"),
)

CURRENCY_CHOICES = (
    ("USD", "USD ($)"),
    ("GBP", "GBP (£)"),
    ("EUR", "EUR (€)"),
)

CURRENCY_SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€"}


class Category(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=60)
    type = models.CharField(max_length=7, choices=TYPE_CHOICES)
    color = models.CharField(max_length=7, default="#2f8a50")
    icon = models.CharField(max_length=40, default="bi-tag")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name", "type"], name="unique_category_per_user_type"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Transaction(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions"
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="transactions"
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    date = models.DateField(default=date.today)
    description = models.CharField(max_length=140)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["user", "date"])]

    def __str__(self):
        return f"{self.description} - {self.amount}"

    @property
    def kind(self):
        return self.category.type

    @property
    def is_income(self):
        return self.category.type == "income"

    @property
    def signed_amount(self):
        return self.amount if self.is_income else -self.amount


class Budget(models.Model):
    """A monthly spending limit for one expense category."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="budgets"
    )
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )

    class Meta:
        ordering = ["-year", "-month", "category__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "month", "year"],
                name="unique_budget_per_category_month",
            )
        ]

    def __str__(self):
        return f"{self.category.name} - {self.month}/{self.year}"

    @property
    def label(self):
        return date(self.year, self.month, 1).strftime("%b %Y")


class Goal(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals"
    )
    name = models.CharField(max_length=80)
    target_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    saved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.name

    @property
    def progress(self):
        if self.target_amount <= 0:
            return 0
        return min(100, int(self.saved_amount / self.target_amount * 100))

    @property
    def remaining(self):
        return max(Decimal("0.00"), self.target_amount - self.saved_amount)


class Profile(models.Model):
    """Per-user preferences, currently the currency used for all amounts."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="USD")

    def __str__(self):
        return f"{self.user.username} ({self.currency})"

    @property
    def symbol(self):
        return CURRENCY_SYMBOLS.get(self.currency, "$")


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
