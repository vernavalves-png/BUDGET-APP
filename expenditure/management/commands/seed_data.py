from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Profile, Role
from expenditure.models import Category

DEFAULT_CATEGORIES = [
    ("Materials & Equipment", "Raw materials, spares, tools and equipment purchases"),
    ("Subcontractor & Services", "Third-party subcontracted work and professional services"),
    ("Travel & Accommodation", "Business travel, lodging and per-diem expenses"),
    ("Office & Admin", "Office supplies, stationery, IT and general admin costs"),
    ("Utilities & Facilities", "Rent, electricity, water, telecom and facility upkeep"),
    ("Miscellaneous", "Any expenditure that doesn't fit another category"),
]

DEMO_USERS = [
    ("admin", "Admin", "User", Role.ADMIN, True),
    ("requester1", "Rita", "Requester", Role.REQUESTER, False),
    ("approver1", "Alex", "ApproverOne", Role.APPROVER1, False),
    ("approver2", "Amina", "ApproverTwo", Role.APPROVER2, False),
]

DEMO_PASSWORD = "ChangeMe123!"


class Command(BaseCommand):
    help = "Creates default expenditure categories and demo users (safe to re-run)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-demo-users",
            action="store_true",
            help="Only create default categories, skip demo user accounts.",
        )

    def handle(self, *args, **options):
        created_categories = 0
        for name, description in DEFAULT_CATEGORIES:
            _, created = Category.objects.get_or_create(name=name, defaults={"description": description})
            created_categories += int(created)
        self.stdout.write(self.style.SUCCESS(f"Categories ready ({created_categories} newly created)."))

        if options["no_demo_users"]:
            return

        for username, first, last, role, is_superuser in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first, "last_name": last, "email": f"{username}@example.com"},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.is_staff = is_superuser
                user.is_superuser = is_superuser
                user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Demo users ready: admin, requester1, approver1, approver2 "
                f"(password for all: {DEMO_PASSWORD}) — change these before going live."
            )
        )
