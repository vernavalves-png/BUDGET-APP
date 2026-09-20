from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name.strip().upper().replace(" ", "-")[:20]
        super().save(*args, **kwargs)

    # --- aggregate helpers used by reports/dashboard ---
    def total_approved_budget(self):
        return self.budget_requests.filter(status=BudgetRequest.Status.APPROVED).aggregate(
            total=models.Sum("approved_amount")
        )["total"] or Decimal("0")

    def total_requested_budget(self):
        return self.budget_requests.exclude(status=BudgetRequest.Status.REJECTED).aggregate(
            total=models.Sum("quotation_amount")
        )["total"] or Decimal("0")

    def total_utilized(self):
        return Payment.objects.filter(
            budget_request__category=self, status=Payment.Status.APPROVED
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")

    def total_remaining(self):
        return self.total_approved_budget() - self.total_utilized()

    def utilization_percent(self):
        approved = self.total_approved_budget()
        if not approved:
            return 0
        return round((self.total_utilized() / approved) * 100, 1)


class BudgetRequest(models.Model):
    """An expenditure item requiring quotation-backed budget approval."""

    class Status(models.TextChoices):
        PENDING_L1 = "PENDING_L1", "Pending Approver 1"
        PENDING_L2 = "PENDING_L2", "Pending Approver 2"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="budget_requests")
    title = models.CharField(max_length=200, help_text="Short description of the expenditure")
    description = models.TextField(blank=True)
    vendor_name = models.CharField(max_length=150, blank=True)
    quotation_amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    quotation_file = models.FileField(upload_to="quotations/%Y/%m/", blank=True, null=True)
    currency = models.CharField(max_length=10, default=settings.CURRENCY_CODE if hasattr(settings, "CURRENCY_CODE") else "AED")

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="budget_requests")
    requested_date = models.DateTimeField(default=timezone.now)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_L1)

    approver1 = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="l1_budget_requests"
    )
    approver1_decision_at = models.DateTimeField(null=True, blank=True)
    approver1_comment = models.CharField(max_length=500, blank=True)

    approver2 = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="l2_budget_requests"
    )
    approver2_decision_at = models.DateTimeField(null=True, blank=True)
    approver2_comment = models.CharField(max_length=500, blank=True)

    approved_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.category.code})"

    def get_absolute_url(self):
        return reverse("budget_detail", args=[self.pk])

    # --- workflow actions ---
    def approve_level1(self, user, comment=""):
        self.approver1 = user
        self.approver1_decision_at = timezone.now()
        self.approver1_comment = comment
        self.status = self.Status.PENDING_L2
        self.save()

    def reject_level1(self, user, comment=""):
        self.approver1 = user
        self.approver1_decision_at = timezone.now()
        self.approver1_comment = comment
        self.status = self.Status.REJECTED
        self.save()

    def approve_level2(self, user, comment="", approved_amount=None):
        self.approver2 = user
        self.approver2_decision_at = timezone.now()
        self.approver2_comment = comment
        self.approved_amount = approved_amount if approved_amount is not None else self.quotation_amount
        self.approved_date = timezone.now()
        self.status = self.Status.APPROVED
        self.save()

    def reject_level2(self, user, comment=""):
        self.approver2 = user
        self.approver2_decision_at = timezone.now()
        self.approver2_comment = comment
        self.status = self.Status.REJECTED
        self.save()

    def resubmit(self):
        """Allow a requester to send a rejected item back into the approval queue."""
        self.status = self.Status.PENDING_L1
        self.approver1 = None
        self.approver1_decision_at = None
        self.approver1_comment = ""
        self.approver2 = None
        self.approver2_decision_at = None
        self.approver2_comment = ""
        self.save()

    # --- money helpers ---
    def committed_payments_total(self):
        """Sum of payments already approved or awaiting approval against this budget."""
        return self.payments.exclude(status=Payment.Status.REJECTED).aggregate(total=models.Sum("amount"))[
            "total"
        ] or Decimal("0")

    def spent_total(self):
        return self.payments.filter(status=Payment.Status.APPROVED).aggregate(total=models.Sum("amount"))[
            "total"
        ] or Decimal("0")

    def available_balance(self):
        if self.status != self.Status.APPROVED or self.approved_amount is None:
            return Decimal("0")
        return self.approved_amount - self.committed_payments_total()

    def utilization_percent(self):
        if not self.approved_amount:
            return 0
        return round((self.spent_total() / self.approved_amount) * 100, 1)


class Payment(models.Model):
    """A payment made/released against an already-approved BudgetRequest."""

    class Status(models.TextChoices):
        PENDING_L1 = "PENDING_L1", "Pending Approver 1"
        PENDING_L2 = "PENDING_L2", "Pending Approver 2"
        APPROVED = "APPROVED", "Approved / Released"
        REJECTED = "REJECTED", "Rejected"

    budget_request = models.ForeignKey(BudgetRequest, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    payee = models.CharField(max_length=150, blank=True, help_text="Vendor / payee name")
    invoice_reference = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(
        max_length=30,
        choices=[("BANK_TRANSFER", "Bank Transfer"), ("CHEQUE", "Cheque"), ("CASH", "Cash"), ("CARD", "Card"), ("OTHER", "Other")],
        default="BANK_TRANSFER",
    )
    proof_file = models.FileField(upload_to="payment_proofs/%Y/%m/", blank=True, null=True)
    remarks = models.CharField(max_length=500, blank=True)

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_requests")
    requested_date = models.DateTimeField(default=timezone.now)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_L1)

    approver1 = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="l1_payments"
    )
    approver1_decision_at = models.DateTimeField(null=True, blank=True)
    approver1_comment = models.CharField(max_length=500, blank=True)

    approver2 = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="l2_payments"
    )
    approver2_decision_at = models.DateTimeField(null=True, blank=True)
    approver2_comment = models.CharField(max_length=500, blank=True)

    paid_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.amount} for {self.budget_request.title}"

    def get_absolute_url(self):
        return reverse("payment_detail", args=[self.pk])

    def approve_level1(self, user, comment=""):
        self.approver1 = user
        self.approver1_decision_at = timezone.now()
        self.approver1_comment = comment
        self.status = self.Status.PENDING_L2
        self.save()

    def reject_level1(self, user, comment=""):
        self.approver1 = user
        self.approver1_decision_at = timezone.now()
        self.approver1_comment = comment
        self.status = self.Status.REJECTED
        self.save()

    def approve_level2(self, user, comment=""):
        self.approver2 = user
        self.approver2_decision_at = timezone.now()
        self.approver2_comment = comment
        self.status = self.Status.APPROVED
        self.paid_date = timezone.now()
        self.save()

    def reject_level2(self, user, comment=""):
        self.approver2 = user
        self.approver2_decision_at = timezone.now()
        self.approver2_comment = comment
        self.status = self.Status.REJECTED
        self.save()
