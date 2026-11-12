from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.models import Merchant


class MerchantMembershipTests(TestCase):
    def test_merchant_can_have_authorized_users(self):
        user = get_user_model().objects.create_user(
            username="merchant_operator",
            password="test-password",
        )

        merchant = Merchant.objects.create(
            name="Test Merchant",
            slug="test-merchant",
        )

        merchant.members.add(user)

        self.assertTrue(merchant.members.filter(pk=user.pk).exists())

    def test_membership_does_not_grant_access_to_other_merchants(self):
        user = get_user_model().objects.create_user(
            username="merchant_operator",
            password="test-password",
        )

        first = Merchant.objects.create(
            name="First Merchant",
            slug="first-merchant",
        )
        second = Merchant.objects.create(
            name="Second Merchant",
            slug="second-merchant",
        )

        first.members.add(user)

        self.assertTrue(first.members.filter(pk=user.pk).exists())
        self.assertFalse(second.members.filter(pk=user.pk).exists())
