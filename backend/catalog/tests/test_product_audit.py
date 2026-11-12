from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import (
    AuditLog,
    Category,
    Merchant,
    Product,
)


class ProductUpdateAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="audit-editor",
            password="test-password",
        )
        cls.merchant = Merchant.objects.create(
            name="Audit Test Merchant",
            slug="audit-test-merchant",
        )
        cls.merchant.members.add(cls.user)

        category = Category.objects.create(
            merchant=cls.merchant,
            name="Computers",
        )
        cls.product = Product.objects.create(
            merchant=cls.merchant,
            category=category,
            name="Workstation",
            sku="AUDIT-001",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def patch_product(self, data):
        return self.client.patch(
            reverse(
                "product-detail",
                kwargs={"pk": self.product.pk},
            )
            + f"?merchant_id={self.merchant.pk}",
            data=data,
            content_type="application/json",
        )

    def test_successful_update_creates_activity(self):
        response = self.patch_product(
            {
                "name": "Premium Workstation",
            }
        )

        self.assertEqual(response.status_code, 200)

        self.product.refresh_from_db()
        self.assertEqual(
            self.product.name,
            "Premium Workstation",
        )

        logs = AuditLog.objects.filter(
            product=self.product,
        )
        self.assertEqual(logs.count(), 1)

        log = logs.get()
        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.action, "product.updated")
        self.assertEqual(
            log.details["changes"]["name"],
            {
                "from": "Workstation",
                "to": "Premium Workstation",
            },
        )

    def test_unchanged_update_creates_no_activity(self):
        response = self.patch_product(
            {
                "name": "Workstation",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(AuditLog.objects.filter(product=self.product).exists())

    def test_invalid_update_creates_no_activity(self):
        response = self.patch_product(
            {
                "status": "not-a-valid-status",
            }
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(AuditLog.objects.filter(product=self.product).exists())
