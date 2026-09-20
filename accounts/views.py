from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import admin_required
from .forms import UserCreateForm, UserEditForm


@admin_required
def user_list(request):
    users = User.objects.select_related("profile").order_by("username")
    return render(request, "accounts/user_list.html", {"users": users})


@admin_required
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User created.")
            return redirect("user_list")
    else:
        form = UserCreateForm()
    return render(request, "accounts/user_form.html", {"form": form, "mode": "Create"})


@admin_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile = user.profile
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "User updated.")
            return redirect("user_list")
    else:
        form = UserEditForm(
            instance=user,
            initial={
                "role": profile.role,
                "department": profile.department,
                "phone": profile.phone,
                "is_active": user.is_active,
            },
        )
    return render(request, "accounts/user_form.html", {"form": form, "mode": "Edit", "target_user": user})
