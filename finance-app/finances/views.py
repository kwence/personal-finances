"""Views for the dashboard, authentication and finance features."""

from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import (
    BudgetForm,
    CategoryForm,
    GoalContributionForm,
    GoalForm,
    LoginForm,
    RegistrationForm,
    TransactionForm,
)
from .models import (
    CURRENCY_CHOICES,
    CURRENCY_SYMBOLS,
    Budget,
    Category,
    Goal,
    Profile,
    Transaction,
)
from .utils import last_months, month_start, parse_month, previous_month, totals


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account is ready.")
            return redirect("dashboard")
    else:
        form = RegistrationForm()
    return render(request, "registration/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                next_url = request.POST.get("next", "")
                if next_url and url_has_allowed_host_and_scheme(
                    next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
                ):
                    return redirect(next_url)
                return redirect("dashboard")
    else:
        form = LoginForm(request)
    return render(request, "registration/login.html", {"form": form})


def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been signed out.")
        return redirect("login")
    return HttpResponseForbidden("Use the sign out button to leave your account.")


@login_required
def currency_change(request):
    """Persist the user's preferred currency and return to the same page."""
    if request.method == "POST":
        code = request.POST.get("currency", "")
        if code in dict(CURRENCY_CHOICES):
            profile, _ = Profile.objects.get_or_create(user=request.user)
            profile.currency = code
            profile.save(update_fields=["currency"])
            messages.success(
                request, f"Currency changed to {code} ({CURRENCY_SYMBOLS[code]})."
            )
        else:
            messages.error(request, "That currency is not supported.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("dashboard")


@login_required
def dashboard(request):
    user = request.user
    today = date.today()
    this_month = user.transactions.filter(
        date__year=today.year, date__month=today.month
    )

    income, expense, month_balance = totals(this_month)
    all_income, all_expense, balance = totals(user.transactions.all())
    savings_rate = int((month_balance / income) * 100) if income > 0 else 0

    months = []
    for year, month, label, start, end in last_months(6, today):
        month_income, month_expense, _ = totals(
            user.transactions.filter(date__range=(start, end))
        )
        months.append(
            {
                "label": label,
                "year": year,
                "income": month_income,
                "expense": month_expense,
            }
        )
    chart_max = max(
        [max(item["income"], item["expense"]) for item in months] + [Decimal("1")]
    )

    breakdown = (
        this_month.filter(category__type="expense")
        .values("category__name", "category__color")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    segments = []
    for row in breakdown:
        share = round(float(row["total"] / expense * 100), 2) if expense > 0 else 0.0
        segments.append(
            {
                "name": row["category__name"],
                "color": row["category__color"],
                "total": row["total"],
                "percent": share,
            }
        )
    stops = []
    running = 0.0
    for segment in segments:
        start = running
        running = round(running + segment["percent"], 2)
        stops.append(f"{segment['color']} {start}% {running}%")
    donut_css = (
        "conic-gradient(" + ",".join(stops) + ")"
        if segments
        else "conic-gradient(#e3f2e7 0% 100%)"
    )

    spent_by_category = dict(
        this_month.filter(category__type="expense")
        .values("category_id")
        .annotate(total=Sum("amount"))
        .values_list("category_id", "total")
    )
    budget_rows = []
    for budget in user.budgets.filter(
        year=today.year, month=today.month
    ).select_related("category"):
        spent = spent_by_category.get(budget.category_id, Decimal("0.00"))
        percent = min(100, int(spent / budget.amount * 100)) if budget.amount else 0
        budget_rows.append(
            {
                "budget": budget,
                "spent": spent,
                "remaining": budget.amount - spent,
                "percent": percent,
                "over": spent > budget.amount,
            }
        )

    context = {
        "months": months,
        "chart_max": chart_max,
        "segments": segments,
        "donut_css": donut_css,
        "income": income,
        "expense": expense,
        "month_balance": month_balance,
        "all_income": all_income,
        "all_expense": all_expense,
        "balance": balance,
        "savings_rate": savings_rate,
        "budget_rows": budget_rows,
        "goals": user.goals.all()[:3],
        "recent_transactions": user.transactions.select_related("category")[:6],
        "transaction_count": user.transactions.count(),
        "category_count": user.categories.count(),
        "today": today,
    }
    return render(request, "finances/dashboard.html", context)


@login_required
def transaction_list(request):
    user = request.user
    transactions = user.transactions.select_related("category").all()
    kind = request.GET.get("type", "")
    category = request.GET.get("category", "")
    month = parse_month(request.GET.get("month", ""))
    query = request.GET.get("q", "").strip()

    if kind in ("income", "expense"):
        transactions = transactions.filter(category__type=kind)
    if category.isdigit():
        transactions = transactions.filter(category_id=int(category))
    if month:
        transactions = transactions.filter(date__year=month.year, date__month=month.month)
    if query:
        transactions = transactions.filter(
            Q(description__icontains=query) | Q(notes__icontains=query)
        )

    page = Paginator(transactions, 12).get_page(request.GET.get("page"))
    months = [previous_month(steps=step) for step in range(12)]
    context = {
        "transactions": page,
        "categories": user.categories.all(),
        "months": months,
        "filters": {"type": kind, "category": category, "month": request.GET.get("month", ""), "q": query},
        "income": totals(transactions)[0],
        "expense": totals(transactions)[1],
    }
    return render(request, "finances/transaction_list.html", context)


@login_required
def transaction_form_view(request, pk=None):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user) if pk else None
    if request.method == "POST":
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            messages.success(
                request,
                "Transaction updated." if transaction else "Transaction added.",
            )
            return redirect("transactions")
    else:
        kind = request.GET.get("type") or (transaction.kind if transaction else "expense")
        form = TransactionForm(user=request.user, instance=transaction, kind=kind)
    return render(
        request,
        "finances/transaction_form.html",
        {
            "form": form,
            "transaction": transaction,
            "kind": form.initial.get("kind"),
            "category_kinds": {
                str(item.id): item.type for item in request.user.categories.all()
            },
        },
    )


@login_required
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == "POST":
        transaction.delete()
        messages.success(request, "Transaction deleted.")
        return redirect("transactions")
    return render(
        request, "finances/transaction_confirm_delete.html", {"transaction": transaction}
    )


@login_required
def category_list(request):
    categories = request.user.categories.all()
    return render(
        request,
        "finances/category_list.html",
        {"categories": categories, "income_categories": categories.filter(type="income"),
         "expense_categories": categories.filter(type="expense")},
    )


@login_required
def category_form_view(request, pk=None):
    category = get_object_or_404(Category, pk=pk, user=request.user) if pk else None
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            messages.success(request, "Category saved.")
            return redirect("categories")
    else:
        form = CategoryForm(instance=category, initial={"type": request.GET.get("type", "expense")})
    return render(
        request, "finances/category_form.html", {"form": form, "category": category}
    )


@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == "POST":
        if category.transactions.exists() or category.budgets.exists():
            messages.error(
                request, "This category is in use. Remove its transactions and budgets first."
            )
            return redirect("categories")
        category.delete()
        messages.success(request, "Category deleted.")
        return redirect("categories")
    return render(
        request, "finances/category_confirm_delete.html", {"category": category}
    )


@login_required
def budget_list(request):
    selected = parse_month(request.GET.get("month", "")) or month_start()
    budgets = (
        request.user.budgets.filter(year=selected.year, month=selected.month)
        .select_related("category")
    )
    spent_by_category = dict(
        request.user.transactions.filter(
            category__type="expense",
            date__year=selected.year,
            date__month=selected.month,
        )
        .values("category_id")
        .annotate(total=Sum("amount"))
        .values_list("category_id", "total")
    )
    rows = []
    for budget in budgets:
        spent = spent_by_category.get(budget.category_id, Decimal("0.00"))
        percent = min(100, int(spent / budget.amount * 100)) if budget.amount else 0
        rows.append(
            {
                "budget": budget,
                "spent": spent,
                "remaining": budget.amount - spent,
                "percent": percent,
                "over": spent > budget.amount,
            }
        )
    context = {
        "rows": rows,
        "selected_month": selected,
        "months": [previous_month(steps=step) for step in range(12)],
    }
    return render(request, "finances/budget_list.html", context)


@login_required
def budget_form_view(request, pk=None):
    budget = get_object_or_404(Budget, pk=pk, user=request.user) if pk else None
    if request.method == "POST":
        form = BudgetForm(request.POST, user=request.user, instance=budget)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            messages.success(request, "Budget saved.")
            return redirect("budgets")
    else:
        today = date.today()
        initial = {"month": today.month, "year": today.year}
        form = BudgetForm(user=request.user, instance=budget, initial=initial)
    return render(request, "finances/budget_form.html", {"form": form, "budget": budget})


@login_required
def budget_delete(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    if request.method == "POST":
        budget.delete()
        messages.success(request, "Budget deleted.")
        return redirect("budgets")
    return render(request, "finances/budget_confirm_delete.html", {"budget": budget})


@login_required
def goal_list(request):
    if request.method == "POST":
        goal = get_object_or_404(Goal, pk=request.POST.get("goal_id"), user=request.user)
        form = GoalContributionForm(request.POST)
        if form.is_valid():
            goal.saved_amount += form.cleaned_data["amount"]
            goal.save(update_fields=["saved_amount"])
            messages.success(request, f"Added to {goal.name}. Nice work!")
            return redirect("goals")
    else:
        form = GoalContributionForm()
    goals = request.user.goals.all()
    total_target = sum((goal.target_amount for goal in goals), Decimal("0.00"))
    total_saved = sum((goal.saved_amount for goal in goals), Decimal("0.00"))
    return render(
        request,
        "finances/goal_list.html",
        {
            "goals": goals,
            "form": form,
            "total_target": total_target,
            "total_saved": total_saved,
            "overall_progress": min(100, int(total_saved / total_target * 100)) if total_target else 0,
        },
    )


@login_required
def goal_form_view(request, pk=None):
    goal = get_object_or_404(Goal, pk=pk, user=request.user) if pk else None
    if request.method == "POST":
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            messages.success(request, "Goal saved.")
            return redirect("goals")
    else:
        form = GoalForm(instance=goal)
    return render(request, "finances/goal_form.html", {"form": form, "goal": goal})


@login_required
def goal_delete(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == "POST":
        goal.delete()
        messages.success(request, "Goal deleted.")
        return redirect("goals")
    return render(request, "finances/goal_confirm_delete.html", {"goal": goal})
