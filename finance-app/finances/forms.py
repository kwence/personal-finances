"""Forms used by the finance app and the authentication pages."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Budget, Category, Goal, Transaction

User = get_user_model()

ICON_CHOICES = [
    ("bi-cash-coin", "Money"),
    ("bi-wallet2", "Wallet"),
    ("bi-house-door", "Home"),
    ("bi-cart3", "Groceries"),
    ("bi-car-front", "Transport"),
    ("bi-lightning-charge", "Utilities"),
    ("bi-heart-pulse", "Health"),
    ("bi-film", "Entertainment"),
    ("bi-book", "Education"),
    ("bi-plane", "Travel"),
    ("bi-gift", "Gifts"),
    ("bi-piggy-bank", "Savings"),
    ("bi-briefcase", "Salary"),
    ("bi-laptop", "Freelance"),
    ("bi-graph-up", "Investments"),
    ("bi-tag", "Other"),
]

MONTH_CHOICES = [(number, name) for number, name in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"], start=1
)]


class StyledFormMixin:
    """Add Bootstrap-friendly placeholders to every visible field."""

    placeholders = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in self.placeholders:
                field.widget.attrs.setdefault("placeholder", self.placeholders[name])


class RegistrationForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text="Used to identify your account. You can use a made-up address for this demo.",
    )
    placeholders = {
        "username": "Choose a username",
        "email": "you@example.com",
        "password1": "At least 8 characters",
        "password2": "Repeat your password",
    }

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class LoginForm(StyledFormMixin, AuthenticationForm):
    placeholders = {"username": "Username", "password": "Password"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username"
        self.fields["password"].label = "Password"


class CategoryForm(StyledFormMixin, forms.ModelForm):
    placeholders = {"name": "e.g. Groceries"}

    class Meta:
        model = Category
        fields = ("name", "type", "color", "icon")
        widgets = {
            "color": forms.TextInput(attrs={"type": "color"}),
            "icon": forms.Select(choices=ICON_CHOICES),
        }


class TransactionForm(StyledFormMixin, forms.ModelForm):
    kind = forms.ChoiceField(
        choices=[("expense", "Expense"), ("income", "Income")],
        label="Transaction type",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )
    placeholders = {
        "amount": "0.00",
        "description": "e.g. Weekly groceries",
        "notes": "Optional details",
    }

    class Meta:
        model = Transaction
        fields = ("kind", "category", "amount", "date", "description", "notes")
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, kind="expense", **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["category"].widget.attrs.update({"data-category-select": "true"})
        if not self.is_bound:
            self.initial.setdefault("kind", kind)
            if kind in dict(self.fields["kind"].choices):
                self.initial.setdefault(
                    "category",
                    self.fields["category"].queryset.filter(type=kind).first(),
                )

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        kind = cleaned.get("kind")
        if category and kind and category.type != kind:
            self.add_error(
                "category", f"Choose a {kind} category, or create one first."
            )
        return cleaned


class BudgetForm(StyledFormMixin, forms.ModelForm):
    placeholders = {"amount": "0.00", "year": "2026"}

    class Meta:
        model = Budget
        fields = ("category", "month", "year", "amount")
        widgets = {"month": forms.Select(choices=MONTH_CHOICES)}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(
            user=user, type="expense"
        )


class GoalForm(StyledFormMixin, forms.ModelForm):
    placeholders = {
        "name": "e.g. Emergency fund",
        "target_amount": "0.00",
        "saved_amount": "0.00",
    }

    class Meta:
        model = Goal
        fields = ("name", "target_amount", "saved_amount", "due_date")
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}

    def clean(self):
        cleaned = super().clean()
        saved = cleaned.get("saved_amount") or 0
        target = cleaned.get("target_amount") or 0
        if saved > target:
            self.add_error("saved_amount", "Saved amount cannot exceed the target.")
        return cleaned


class GoalContributionForm(forms.Form):
    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "0.00", "step": "0.01"}),
        label=False,
    )
