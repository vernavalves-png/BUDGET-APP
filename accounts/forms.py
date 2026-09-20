from django import forms
from django.contrib.auth.models import User

from .models import Profile, Role


def _style(form):
    for name, field in form.fields.items():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault("class", "form-check-input")
        elif isinstance(field.widget, forms.Select):
            field.widget.attrs.setdefault("class", "form-select")
        else:
            field.widget.attrs.setdefault("class", "form-control")


class UserCreateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8, label="Password")
    role = forms.ChoiceField(choices=Role.choices)
    department = forms.CharField(max_length=100, required=False)
    phone = forms.CharField(max_length=30, required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data["role"]
            profile.department = self.cleaned_data["department"]
            profile.phone = self.cleaned_data["phone"]
            profile.save()
        return user


class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Role.choices)
    department = forms.CharField(max_length=100, required=False)
    phone = forms.CharField(max_length=30, required=False)
    new_password = forms.CharField(
        widget=forms.PasswordInput, required=False, min_length=8,
        label="Reset password (leave blank to keep current)",
    )
    is_active = forms.BooleanField(required=False, label="Active (can log in)")

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("new_password"):
            user.set_password(self.cleaned_data["new_password"])
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data["role"]
            profile.department = self.cleaned_data["department"]
            profile.phone = self.cleaned_data["phone"]
            profile.save()
        return user
