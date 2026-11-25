"""Create a ready-to-explore demo account with six months of sample data."""

import calendar
import random
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from finances.models import Budget, Category, Goal, Transaction
from finances.utils import previous_month

User = get_user_model()

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "DemoPass123!"

EXPENSE_CATEGORIES = [
    ("Groceries", "#45a86d", "bi-cart3"),
    ("Rent", "#7aa6d8", "bi-house-door"),
    ("Transport", "#e0a458", "bi-car-front"),
    ("Utilities", "#8e7cc3", "bi-lightning-charge"),
    ("Dining out", "#d98f6e", "bi-film"),
    ("Shopping", "#d47ba5", "bi-bag"),
    ("Health", "#5eb5ad", "bi-heart-pulse"),
    ("Entertainment", "#9b8ad1", "bi-film"),
    ("Travel", "#6a9fd8", "bi-plane"),
]

INCOME_CATEGORIES = [
    ("Salary", "#2f8a50", "bi-briefcase"),
    ("Freelance", "#3f9f7a", "bi-laptop"),
    ("Investments", "#5b8bc4", "bi-graph-up"),
]

BUDGETS = {
    "Groceries": 650,
    "Rent": 1200,
    "Transport": 220,
    "Utilities": 160,
    "Dining out": 200,
    "Shopping": 250,
    "Health": 100,
    "Entertainment": 120,
}


class Command(BaseCommand):
    help = "Seed (or refresh) the demo user with six months of realistic sample data."

    def handle(self, *args, **options):
        verbose = options.get("verbosity", 1) > 0
        rng = random.Random(2026)
        user, created = User.objects.get_or_create(
            username=DEMO_USERNAME,
            defaults={"email": "demo@example.com", "first_name": "Demo"},
        )
        user.set_password(DEMO_PASSWORD)
        user.save()

        # Refresh only the demo account's data so the command is idempotent.
        user.transactions.all().delete()
        user.budgets.all().delete()
        user.goals.all().delete()
        user.categories.all().delete()

        categories = {}
        for name, color, icon in EXPENSE_CATEGORIES:
            categories[name] = Category.objects.create(
                user=user, name=name, type="expense", color=color, icon=icon
            )
        for name, color, icon in INCOME_CATEGORIES:
            categories[name] = Category.objects.create(
                user=user, name=name, type="income", color=color, icon=icon
            )

        today = date.today()
        for steps in range(5, -1, -1):
            first = previous_month(today, steps)
            last_day = calendar.monthrange(first.year, first.month)[1]

            def day(number):
                # Don't put sample transactions in the future.
                limit = min(last_day, today.day) if steps == 0 else last_day
                return date(first.year, first.month, min(number, limit))

            self._add(user, categories, "Salary", day(1), Decimal("3200.00"), "Monthly salary")
            if steps in (5, 3, 1):
                self._add(
                    user, categories, "Freelance", day(17),
                    Decimal(str(rng.randint(180, 520))), "Website redesign project",
                )
            if steps == 2:
                self._add(
                    user, categories, "Investments", day(21),
                    Decimal("145.00"), "Dividend payout",
                )

            self._add(user, categories, "Rent", day(2), Decimal("1150.00"), "Apartment rent")
            for index in range(4):
                self._add(
                    user, categories, "Groceries", day(5 + index * 7),
                    Decimal(str(rng.randint(42, 118))),
                    rng.choice(["Weekly groceries", "Farmers market", "Supermarket run"]),
                )
            for index in range(3):
                self._add(
                    user, categories, "Transport", day(4 + index * 9),
                    Decimal(str(rng.randint(18, 62))),
                    rng.choice(["Metro card top-up", "Fuel", "Ride share"]),
                )
            self._add(
                user, categories, "Utilities", day(8),
                Decimal(str(rng.randint(95, 148))), "Electricity and internet",
            )
            for index in range(2):
                self._add(
                    user, categories, "Dining out", day(11 + index * 12),
                    Decimal(str(rng.randint(22, 74))),
                    rng.choice(["Dinner with friends", "Lunch downtown", "Coffee and pastry"]),
                )
            self._add(
                user, categories, "Shopping", day(23),
                Decimal(str(rng.randint(48, 210))), rng.choice(["Clothes", "Home supplies", "Books"]),
            )
            self._add(
                user, categories, "Entertainment", day(27),
                Decimal(str(rng.randint(16, 58))), rng.choice(["Cinema", "Streaming", "Concert ticket"]),
            )
            if steps == 4:
                self._add(user, categories, "Travel", day(14), Decimal("480.00"), "Weekend getaway")
            if steps == 0:
                self._add(user, categories, "Health", day(12), Decimal("75.00"), "Pharmacy")

        current = date.today()
        for name, amount in BUDGETS.items():
            Budget.objects.create(
                user=user,
                category=categories[name],
                month=current.month,
                year=current.year,
                amount=Decimal(str(amount)),
            )

        Goal.objects.create(
            user=user, name="Emergency fund", target_amount=Decimal("6000.00"),
            saved_amount=Decimal("3650.00"), due_date=date(current.year + 1, current.month, 1),
        )
        Goal.objects.create(
            user=user, name="Summer trip", target_amount=Decimal("2500.00"),
            saved_amount=Decimal("980.00"),
        )
        Goal.objects.create(
            user=user, name="New laptop", target_amount=Decimal("1800.00"),
            saved_amount=Decimal("450.00"),
        )

        if verbose:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Demo data ready: {user.transactions.count()} transactions, "
                    f"{user.categories.count()} categories, {user.budgets.count()} budgets, "
                    f"{user.goals.count()} goals."
                )
            )
            self.stdout.write(f"Sign in with: {DEMO_USERNAME} / {DEMO_PASSWORD}")

    @staticmethod
    def _add(user, categories, category_name, day, amount, description):
        Transaction.objects.create(
            user=user,
            category=categories[category_name],
            amount=amount,
            date=day,
            description=description,
        )
