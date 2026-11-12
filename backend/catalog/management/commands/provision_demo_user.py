from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Merchant


class Command(BaseCommand):
    help = "Provision a local MerchantOps demo operator."

    @transaction.atomic
    def handle(self, *args, **options):
        merchant = Merchant.objects.filter(slug="assessment-merchant-01").first()

        if merchant is None:
            raise CommandError(
                "Seeded Northstar merchant not found. " "Run seed_catalog first."
            )

        User = get_user_model()
        username = "demo_operator"

        user = User.objects.filter(username=username).first()

        if user is None:
            password = getpass("Demo user password: ")

            if len(password) < 8:
                raise CommandError("Password must contain at least 8 characters.")

            user = User.objects.create_user(
                username=username,
                password=password,
            )

            self.stdout.write("Created demo operator.")
        else:
            self.stdout.write("Demo operator already exists; password unchanged.")

        merchant.members.add(user)

        self.stdout.write(
            self.style.SUCCESS(
                f"Username: {username}\n"
                f"Merchant: {merchant.name}\n"
                f"Merchant ID: {merchant.pk}\n"
                "Membership verified."
            )
        )
