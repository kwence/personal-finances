from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("currency/", views.currency_change, name="currency_change"),
    path("transactions/", views.transaction_list, name="transactions"),
    path("transactions/new/", views.transaction_form_view, name="transaction_create"),
    path("transactions/<int:pk>/edit/", views.transaction_form_view, name="transaction_edit"),
    path("transactions/<int:pk>/delete/", views.transaction_delete, name="transaction_delete"),
    path("categories/", views.category_list, name="categories"),
    path("categories/new/", views.category_form_view, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_form_view, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("budgets/", views.budget_list, name="budgets"),
    path("budgets/new/", views.budget_form_view, name="budget_create"),
    path("budgets/<int:pk>/edit/", views.budget_form_view, name="budget_edit"),
    path("budgets/<int:pk>/delete/", views.budget_delete, name="budget_delete"),
    path("goals/", views.goal_list, name="goals"),
    path("goals/new/", views.goal_form_view, name="goal_create"),
    path("goals/<int:pk>/edit/", views.goal_form_view, name="goal_edit"),
    path("goals/<int:pk>/delete/", views.goal_delete, name="goal_delete"),
]
