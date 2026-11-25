"""Automated tests for models, utilities, views and the demo seed command."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .context_processors import currency as currency_context
from .models import Budget, Category, Goal, Profile, Transaction
from .templatetags.currency_tags import money
from .utils import last_months, month_start, previous_month, totals

User = get_user_model()


class FinanceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="TestPass123!"
        )
        self.other = User.objects.create_user(
            username="other", email="other@example.com", password="OtherPass123!"
        )
        self.income = Category.objects.create(
            user=self.user, name="Salary", type="income", color="#2f8a50"
        )
        self.expense = Category.objects.create(
            user=self.user, name="Food", type="expense", color="#45a86d"
        )
        self.other_expense = Category.objects.create(
            user=self.other, name="Secret", type="expense"
        )

    def add_transaction(self, category, amount, when=None, user=None, description="Item"):
        return Transaction.objects.create(
            user=user or self.user,
            category=category,
            amount=Decimal(str(amount)),
            date=when or date.today(),
            description=description,
        )


class ModelTests(FinanceTestCase):
    def test_transaction_kind_and_signed_amount(self):
        income = self.add_transaction(self.income, "100.00")
        expense = self.add_transaction(self.expense, "40.50")
        self.assertEqual(income.kind, "income")
        self.assertTrue(income.is_income)
        self.assertEqual(income.signed_amount, Decimal("100.00"))
        self.assertFalse(expense.is_income)
        self.assertEqual(expense.signed_amount, Decimal("-40.50"))

    def test_category_string_and_budget_label(self):
        budget = Budget.objects.create(
            user=self.user, category=self.expense, month=3, year=2026, amount=Decimal("200")
        )
        self.assertEqual(str(self.expense), "Food (Expense)")
        self.assertEqual(budget.label, "Mar 2026")

    def test_goal_progress_and_remaining(self):
        goal = Goal.objects.create(
            user=self.user,
            name="Trip",
            target_amount=Decimal("1000"),
            saved_amount=Decimal("250"),
        )
        self.assertEqual(goal.progress, 25)
        self.assertEqual(goal.remaining, Decimal("750"))
        goal.saved_amount = Decimal("1400")
        self.assertEqual(goal.progress, 100)
        self.assertEqual(goal.remaining, Decimal("0"))


class UtilityTests(TestCase):
    def test_month_helpers(self):
        self.assertEqual(previous_month(date(2026, 1, 15)), date(2025, 12, 1))
        months = last_months(3, date(2026, 3, 10))
        self.assertEqual(
            [(item[0], item[1]) for item in months],
            [(2026, 1), (2026, 2), (2026, 3)],
        )
        self.assertEqual(month_start(date(2026, 7, 22)), date(2026, 7, 1))

    def test_totals(self):
        user = User.objects.create_user(username="u", password="TestPass123!")
        income = Category.objects.create(user=user, name="Pay", type="income")
        expense = Category.objects.create(user=user, name="Food", type="expense")
        Transaction.objects.create(user=user, category=income, amount=Decimal("500"), description="Pay")
        Transaction.objects.create(user=user, category=expense, amount=Decimal("120"), description="Food")
        self.assertEqual(totals(user.transactions.all()), (Decimal("500"), Decimal("120"), Decimal("380")))


class AuthViewTests(TestCase):
    def test_register_page_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newbie",
                "email": "newbie@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(User.objects.filter(username="newbie").exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), User.objects.get(username="newbie").pk)

    def test_login_page_accepts_valid_credentials(self):
        User.objects.create_user(username="loginuser", password="TestPass123!")
        response = self.client.post(
            reverse("login"), {"username": "loginuser", "password": "TestPass123!"}
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_rejects_bad_password(self):
        User.objects.create_user(username="loginuser", password="TestPass123!")
        response = self.client.post(
            reverse("login"), {"username": "loginuser", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        self.client.force_login(User.objects.create_user(username="u", password="TestPass123!"))
        self.assertEqual(self.client.get(reverse("logout")).status_code, 403)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))


class DashboardViewTests(FinanceTestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_dashboard_shows_only_current_user_data(self):
        self.add_transaction(self.income, "1000", description="My pay")
        self.add_transaction(self.expense, "250", description="My food")
        self.add_transaction(self.other_expense, "9999", user=self.other, description="Hidden")
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My pay")
        self.assertNotContains(response, "Hidden")
        self.assertEqual(response.context["balance"], Decimal("750"))
        self.assertEqual(response.context["expense"], Decimal("250"))

    def test_dashboard_empty_state(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "No expenses logged this month")
        self.assertEqual(response.context["savings_rate"], 0)


class FinanceViewTests(FinanceTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_transaction_create_from_post(self):
        response = self.client.post(
            reverse("transaction_create"),
            {
                "kind": "expense",
                "category": self.expense.pk,
                "amount": "35.50",
                "date": date.today().isoformat(),
                "description": "Lunch",
                "notes": "",
            },
        )
        self.assertRedirects(response, reverse("transactions"))
        self.assertTrue(self.user.transactions.filter(description="Lunch").exists())

    def test_transaction_form_rejects_mismatched_category_type(self):
        response = self.client.post(
            reverse("transaction_create"),
            {
                "kind": "income",
                "category": self.expense.pk,
                "amount": "35.50",
                "date": date.today().isoformat(),
                "description": "Oops",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.user.transactions.filter(description="Oops").exists())
        self.assertContains(response, "Choose a income category")

    def test_cannot_edit_or_delete_another_users_transaction(self):
        foreign = self.add_transaction(
            self.other_expense, "77", user=self.other, description="Foreign"
        )
        for name in ("transaction_edit", "transaction_delete"):
            response = self.client.get(reverse(name, args=[foreign.pk]))
            self.assertEqual(response.status_code, 404)
            response = self.client.post(reverse(name, args=[foreign.pk]))
            self.assertEqual(response.status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=foreign.pk).exists())

    def test_transaction_filters(self):
        self.add_transaction(self.income, "500", description="Salary")
        self.add_transaction(self.expense, "30", description="Groceries")
        response = self.client.get(reverse("transactions"), {"type": "expense", "q": "groc"})
        results = list(response.context["transactions"].object_list)
        self.assertEqual([item.description for item in results], ["Groceries"])
        self.assertContains(response, "Groceries")

    def test_category_delete_protected_when_used(self):
        self.add_transaction(self.expense, "20")
        response = self.client.post(reverse("category_delete", args=[self.expense.pk]))
        self.assertRedirects(response, reverse("categories"))
        self.assertTrue(Category.objects.filter(pk=self.expense.pk).exists())

    def test_budget_list_shows_spending(self):
        self.add_transaction(self.expense, "40")
        today = date.today()
        Budget.objects.create(
            user=self.user, category=self.expense, month=today.month, year=today.year,
            amount=Decimal("100"),
        )
        response = self.client.get(reverse("budgets"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["rows"][0]["spent"], Decimal("40"))
        self.assertEqual(response.context["rows"][0]["percent"], 40)
        self.assertContains(response, "60.00 remaining")

    def test_goal_contribution(self):
        goal = Goal.objects.create(
            user=self.user, name="Fund", target_amount=Decimal("500"), saved_amount=Decimal("100")
        )
        response = self.client.post(reverse("goals"), {"goal_id": goal.pk, "amount": "50"})
        self.assertRedirects(response, reverse("goals"))
        goal.refresh_from_db()
        self.assertEqual(goal.saved_amount, Decimal("150"))

    def test_cannot_contribute_to_another_users_goal(self):
        goal = Goal.objects.create(
            user=self.other, name="Foreign", target_amount=Decimal("500")
        )
        response = self.client.post(reverse("goals"), {"goal_id": goal.pk, "amount": "50"})
        self.assertEqual(response.status_code, 404)
        goal.refresh_from_db()
        self.assertEqual(goal.saved_amount, Decimal("0"))


class MoneyFormatTests(TestCase):
    def test_money_tag_formats_all_currencies(self):
        self.assertEqual(money({"currency": "USD"}, Decimal("1234.5")), "$1,234.50")
        self.assertEqual(money({"currency": "GBP"}, Decimal("1234.5")), "£1,234.50")
        self.assertEqual(money({"currency": "EUR"}, Decimal("1234.5")), "€1,234.50")

    def test_money_tag_handles_negative_and_missing_values(self):
        self.assertEqual(money({"currency": "GBP"}, Decimal("-25.5")), "-£25.50")
        self.assertEqual(money({"currency": "EUR"}, None), "€0.00")
        self.assertEqual(money({}, "12.3"), "$12.30")


class CurrencyViewTests(FinanceTestCase):
    def test_profile_created_with_user(self):
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_context_processor_defaults_and_preference(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        self.assertEqual(currency_context(request)["currency"], "USD")
        self.user.profile.currency = "EUR"
        self.user.profile.save(update_fields=["currency"])
        request.user = self.user
        context = currency_context(request)
        self.assertEqual(context["currency"], "EUR")
        self.assertEqual(context["currency_symbol"], "€")
        self.assertEqual(len(context["currency_choices"]), 3)

    def test_currency_change_requires_login(self):
        response = self.client.post(reverse("currency_change"), {"currency": "GBP"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_currency_change_updates_profile(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("currency_change"),
            {"currency": "GBP", "next": reverse("transactions")},
        )
        self.assertRedirects(response, reverse("transactions"))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.currency, "GBP")

    def test_invalid_currency_is_ignored(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("currency_change"), {"currency": "JPY", "next": reverse("dashboard")}
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.currency, "USD")

    def test_dashboard_uses_chosen_currency(self):
        self.add_transaction(self.income, "100", description="Payday")
        self.user.profile.currency = "EUR"
        self.user.profile.save(update_fields=["currency"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "€100.00")
        self.assertNotContains(response, "$100.00")


class SeedCommandTests(TestCase):
    def test_seed_demo_is_idempotent(self):
        call_command("seed_demo", verbosity=0)
        user = User.objects.get(username="demo")
        first_count = user.transactions.count()
        self.assertEqual(user.check_password("DemoPass123!"), True)
        self.assertEqual(first_count, user.transactions.count())
        self.assertEqual(user.categories.count(), 12)
        self.assertEqual(user.budgets.count(), 8)
        self.assertEqual(user.goals.count(), 3)
        call_command("seed_demo", verbosity=0)
        self.assertEqual(user.transactions.count(), first_count)
        self.assertEqual(user.categories.count(), 12)
