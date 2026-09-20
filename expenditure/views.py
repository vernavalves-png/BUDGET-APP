from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required, role_required
from .forms import ApprovalDecisionForm, BudgetRequestForm, CategoryForm, FinalApprovalDecisionForm, PaymentForm
from .models import BudgetRequest, Category, Payment


# ---------------------------------------------------------------- dashboard
@login_required
def dashboard(request):
    profile = request.user.profile
    categories = Category.objects.filter(is_active=True)

    category_rows = []
    total_approved = Decimal("0")
    total_utilized = Decimal("0")
    for cat in categories:
        approved = cat.total_approved_budget()
        utilized = cat.total_utilized()
        total_approved += approved
        total_utilized += utilized
        category_rows.append(
            {
                "category": cat,
                "approved": approved,
                "utilized": utilized,
                "remaining": approved - utilized,
                "percent": cat.utilization_percent(),
            }
        )

    pending_budget_l1 = BudgetRequest.objects.filter(status=BudgetRequest.Status.PENDING_L1).count()
    pending_budget_l2 = BudgetRequest.objects.filter(status=BudgetRequest.Status.PENDING_L2).count()
    pending_payment_l1 = Payment.objects.filter(status=Payment.Status.PENDING_L1).count()
    pending_payment_l2 = Payment.objects.filter(status=Payment.Status.PENDING_L2).count()

    my_pending_actions = 0
    if profile.is_approver1:
        my_pending_actions += pending_budget_l1 + pending_payment_l1
    if profile.is_approver2:
        my_pending_actions += pending_budget_l2 + pending_payment_l2

    recent_budgets = BudgetRequest.objects.select_related("category", "requested_by")
    recent_payments = Payment.objects.select_related("budget_request", "requested_by")
    if not profile.is_admin and not (profile.is_approver1 or profile.is_approver2):
        recent_budgets = recent_budgets.filter(requested_by=request.user)
        recent_payments = recent_payments.filter(requested_by=request.user)
    recent_budgets = recent_budgets[:8]
    recent_payments = recent_payments[:8]

    context = {
        "category_rows": category_rows,
        "total_approved": total_approved,
        "total_utilized": total_utilized,
        "total_remaining": total_approved - total_utilized,
        "overall_percent": round((total_utilized / total_approved) * 100, 1) if total_approved else 0,
        "pending_budget_l1": pending_budget_l1,
        "pending_budget_l2": pending_budget_l2,
        "pending_payment_l1": pending_payment_l1,
        "pending_payment_l2": pending_payment_l2,
        "my_pending_actions": my_pending_actions,
        "recent_budgets": recent_budgets,
        "recent_payments": recent_payments,
    }
    return render(request, "expenditure/dashboard.html", context)


# ---------------------------------------------------------------- categories
@admin_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, "expenditure/category_list.html", {"categories": categories})


@admin_required
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category created.")
            return redirect("category_list")
    else:
        form = CategoryForm()
    return render(request, "expenditure/category_form.html", {"form": form, "mode": "Create"})


@admin_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated.")
            return redirect("category_list")
    else:
        form = CategoryForm(instance=category)
    return render(request, "expenditure/category_form.html", {"form": form, "mode": "Edit"})


# ------------------------------------------------------------ budget requests
@login_required
def budget_list(request):
    profile = request.user.profile
    qs = BudgetRequest.objects.select_related("category", "requested_by")

    status = request.GET.get("status")
    scope = request.GET.get("scope", "all")

    if scope == "mine":
        qs = qs.filter(requested_by=request.user)
    elif scope == "pending_me":
        if profile.is_approver1:
            qs = qs.filter(status=BudgetRequest.Status.PENDING_L1)
        elif profile.is_approver2:
            qs = qs.filter(status=BudgetRequest.Status.PENDING_L2)
        else:
            qs = qs.none()
    elif not (profile.is_admin or profile.is_approver1 or profile.is_approver2):
        qs = qs.filter(requested_by=request.user)

    if status:
        qs = qs.filter(status=status)

    return render(
        request,
        "expenditure/budget_list.html",
        {"budget_requests": qs, "status_choices": BudgetRequest.Status.choices, "scope": scope, "status": status},
    )


@role_required("REQUESTER")
def budget_create(request):
    if request.method == "POST":
        form = BudgetRequestForm(request.POST, request.FILES)
        if form.is_valid():
            budget_request = form.save(commit=False)
            budget_request.requested_by = request.user
            budget_request.save()
            messages.success(request, "Budget request submitted for approval.")
            return redirect("budget_detail", pk=budget_request.pk)
    else:
        form = BudgetRequestForm()
    return render(request, "expenditure/budget_form.html", {"form": form})


@login_required
def budget_detail(request, pk):
    budget_request = get_object_or_404(BudgetRequest.objects.select_related("category", "requested_by"), pk=pk)
    profile = request.user.profile

    can_view = (
        profile.is_admin
        or profile.is_approver1
        or profile.is_approver2
        or budget_request.requested_by_id == request.user.id
    )
    if not can_view:
        messages.error(request, "You don't have permission to view that budget request.")
        return redirect("budget_list")

    can_act_l1 = profile.is_approver1 and budget_request.status == BudgetRequest.Status.PENDING_L1
    can_act_l2 = profile.is_approver2 and budget_request.status == BudgetRequest.Status.PENDING_L2
    can_resubmit = (
        budget_request.requested_by_id == request.user.id and budget_request.status == BudgetRequest.Status.REJECTED
    )

    l1_form = ApprovalDecisionForm()
    l2_form = FinalApprovalDecisionForm(initial={"approved_amount": budget_request.quotation_amount})

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "level1" and can_act_l1:
            l1_form = ApprovalDecisionForm(request.POST)
            if l1_form.is_valid():
                comment = l1_form.cleaned_data["comment"]
                if l1_form.cleaned_data["decision"] == "approve":
                    budget_request.approve_level1(request.user, comment)
                    messages.success(request, "Approved at level 1; sent to Approver 2.")
                else:
                    budget_request.reject_level1(request.user, comment)
                    messages.warning(request, "Budget request rejected.")
                return redirect("budget_detail", pk=pk)
        elif action == "level2" and can_act_l2:
            l2_form = FinalApprovalDecisionForm(request.POST)
            if l2_form.is_valid():
                comment = l2_form.cleaned_data["comment"]
                if l2_form.cleaned_data["decision"] == "approve":
                    amount = l2_form.cleaned_data.get("approved_amount") or budget_request.quotation_amount
                    budget_request.approve_level2(request.user, comment, approved_amount=amount)
                    messages.success(request, "Budget approved. Payments can now be raised against it.")
                else:
                    budget_request.reject_level2(request.user, comment)
                    messages.warning(request, "Budget request rejected.")
                return redirect("budget_detail", pk=pk)
        elif action == "resubmit" and can_resubmit:
            budget_request.resubmit()
            messages.info(request, "Budget request resubmitted for approval.")
            return redirect("budget_detail", pk=pk)

    context = {
        "budget_request": budget_request,
        "can_act_l1": can_act_l1,
        "can_act_l2": can_act_l2,
        "can_resubmit": can_resubmit,
        "l1_form": l1_form,
        "l2_form": l2_form,
        "payments": budget_request.payments.select_related("requested_by").all(),
    }
    return render(request, "expenditure/budget_detail.html", context)


# ---------------------------------------------------------------- payments
@login_required
def payment_list(request):
    profile = request.user.profile
    qs = Payment.objects.select_related("budget_request", "budget_request__category", "requested_by")

    scope = request.GET.get("scope", "all")
    status = request.GET.get("status")

    if scope == "mine":
        qs = qs.filter(requested_by=request.user)
    elif scope == "pending_me":
        if profile.is_approver1:
            qs = qs.filter(status=Payment.Status.PENDING_L1)
        elif profile.is_approver2:
            qs = qs.filter(status=Payment.Status.PENDING_L2)
        else:
            qs = qs.none()
    elif not (profile.is_admin or profile.is_approver1 or profile.is_approver2):
        qs = qs.filter(requested_by=request.user)

    if status:
        qs = qs.filter(status=status)

    return render(
        request,
        "expenditure/payment_list.html",
        {"payments": qs, "status_choices": Payment.Status.choices, "scope": scope, "status": status},
    )


@role_required("REQUESTER")
def payment_create(request):
    initial = {}
    budget_pk = request.GET.get("budget_request")
    if budget_pk:
        initial["budget_request"] = budget_pk

    if request.method == "POST":
        form = PaymentForm(request.POST, request.FILES)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.requested_by = request.user
            payment.save()
            messages.success(request, "Payment request submitted for approval.")
            return redirect("payment_detail", pk=payment.pk)
    else:
        form = PaymentForm(initial=initial)
    return render(request, "expenditure/payment_form.html", {"form": form})


@login_required
def payment_detail(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related("budget_request", "budget_request__category", "requested_by"), pk=pk
    )
    profile = request.user.profile

    can_view = (
        profile.is_admin
        or profile.is_approver1
        or profile.is_approver2
        or payment.requested_by_id == request.user.id
    )
    if not can_view:
        messages.error(request, "You don't have permission to view that payment.")
        return redirect("payment_list")

    can_act_l1 = profile.is_approver1 and payment.status == Payment.Status.PENDING_L1
    can_act_l2 = profile.is_approver2 and payment.status == Payment.Status.PENDING_L2

    l1_form = ApprovalDecisionForm()
    l2_form = ApprovalDecisionForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "level1" and can_act_l1:
            l1_form = ApprovalDecisionForm(request.POST)
            if l1_form.is_valid():
                comment = l1_form.cleaned_data["comment"]
                if l1_form.cleaned_data["decision"] == "approve":
                    payment.approve_level1(request.user, comment)
                    messages.success(request, "Payment approved at level 1; sent to Approver 2.")
                else:
                    payment.reject_level1(request.user, comment)
                    messages.warning(request, "Payment rejected.")
                return redirect("payment_detail", pk=pk)
        elif action == "level2" and can_act_l2:
            l2_form = ApprovalDecisionForm(request.POST)
            if l2_form.is_valid():
                comment = l2_form.cleaned_data["comment"]
                if l2_form.cleaned_data["decision"] == "approve":
                    payment.approve_level2(request.user, comment)
                    messages.success(request, "Payment approved and marked as released.")
                else:
                    payment.reject_level2(request.user, comment)
                    messages.warning(request, "Payment rejected.")
                return redirect("payment_detail", pk=pk)

    context = {
        "payment": payment,
        "can_act_l1": can_act_l1,
        "can_act_l2": can_act_l2,
        "l1_form": l1_form,
        "l2_form": l2_form,
    }
    return render(request, "expenditure/payment_detail.html", context)


# ---------------------------------------------------------------- reports
@login_required
def report_category(request):
    categories = Category.objects.all()
    rows = []
    totals = {"approved": Decimal("0"), "utilized": Decimal("0")}
    for cat in categories:
        approved = cat.total_approved_budget()
        utilized = cat.total_utilized()
        totals["approved"] += approved
        totals["utilized"] += utilized
        rows.append(
            {
                "category": cat,
                "approved": approved,
                "utilized": utilized,
                "remaining": approved - utilized,
                "percent": cat.utilization_percent(),
            }
        )
    totals["remaining"] = totals["approved"] - totals["utilized"]
    totals["percent"] = round((totals["utilized"] / totals["approved"]) * 100, 1) if totals["approved"] else 0
    return render(request, "expenditure/report_category.html", {"rows": rows, "totals": totals})


@login_required
def report_budget(request):
    qs = BudgetRequest.objects.filter(status=BudgetRequest.Status.APPROVED).select_related("category", "requested_by")
    category_id = request.GET.get("category")
    if category_id:
        qs = qs.filter(category_id=category_id)

    rows = []
    for br in qs:
        spent = br.spent_total()
        rows.append(
            {
                "budget_request": br,
                "approved": br.approved_amount,
                "spent": spent,
                "remaining": br.approved_amount - spent,
                "percent": br.utilization_percent(),
            }
        )
    return render(
        request,
        "expenditure/report_budget.html",
        {"rows": rows, "categories": Category.objects.all(), "selected_category": category_id},
    )
