from django.contrib import admin

from .models import Budget, Category, Goal, Profile, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "user", "color")
    list_filter = ("type",)
    search_fields = ("name", "user__username")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("description", "user", "category", "amount", "date")
    list_filter = ("category__type", "date")
    search_fields = ("description", "user__username")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("category", "user", "month", "year", "amount")
    list_filter = ("year", "month")


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "target_amount", "saved_amount", "due_date")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "currency")
