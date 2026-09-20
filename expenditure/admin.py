from django.contrib import admin

from .models import BudgetRequest, Category, Payment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "total_approved_budget", "total_utilized")
    search_fields = ("name", "code")


@admin.register(BudgetRequest)
class BudgetRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "quotation_amount", "approved_amount", "requested_by", "requested_date")
    list_filter = ("status", "category")
    search_fields = ("title", "vendor_name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("budget_request", "amount", "status", "requested_by", "requested_date")
    list_filter = ("status",)
    search_fields = ("budget_request__title", "payee", "invoice_reference")
