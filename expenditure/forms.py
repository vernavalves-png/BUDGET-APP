from django import forms

from .models import BudgetRequest, Category, Payment


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}


class BudgetRequestForm(forms.ModelForm):
    class Meta:
        model = BudgetRequest
        fields = ["category", "title", "description", "vendor_name", "quotation_amount", "quotation_file"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        for name, field in self.fields.items():
            css = "form-control"
            if isinstance(field.widget, (forms.Select,)):
                css = "form-select"
            if isinstance(field.widget, forms.CheckboxInput):
                css = "form-check-input"
            field.widget.attrs.setdefault("class", css)


class ApprovalDecisionForm(forms.Form):
    DECISION_CHOICES = [("approve", "Approve"), ("reject", "Reject")]
    decision = forms.ChoiceField(choices=DECISION_CHOICES, widget=forms.RadioSelect)
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}))


class FinalApprovalDecisionForm(forms.Form):
    """Used at Approver 2 stage of a BudgetRequest, allows adjusting the final approved amount."""
    DECISION_CHOICES = [("approve", "Approve"), ("reject", "Reject")]
    decision = forms.ChoiceField(choices=DECISION_CHOICES, widget=forms.RadioSelect)
    approved_amount = forms.DecimalField(
        max_digits=14, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        help_text="Defaults to the quoted amount if left blank.",
    )
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}))


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["budget_request", "amount", "payee", "invoice_reference", "payment_method", "proof_file", "remarks"]
        widgets = {"remarks": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["budget_request"].queryset = BudgetRequest.objects.filter(status=BudgetRequest.Status.APPROVED)
        for name, field in self.fields.items():
            css = "form-control"
            if isinstance(field.widget, (forms.Select,)):
                css = "form-select"
            field.widget.attrs.setdefault("class", css)

    def clean(self):
        cleaned = super().clean()
        budget_request = cleaned.get("budget_request")
        amount = cleaned.get("amount")
        if budget_request and amount:
            balance = budget_request.available_balance()
            if amount > balance:
                raise forms.ValidationError(
                    f"Amount exceeds the available approved balance of {balance} for this budget item."
                )
        return cleaned
