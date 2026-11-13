from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from catalog.models import (
    AuditLog,
    Category,
    Inventory,
    Merchant,
    Product,
    ProductVariant,
)


class InventoryAdjustmentAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="merchant-operator",
            password="test-password",
        )

        cls.merchant = Merchant.objects.create(
            name="First Merchant",
            slug="first-merchant",
        )
        cls.merchant.members.add(cls.user)

        cls.other_merchant = Merchant.objects.create(
            name="Second Merchant",
            slug="second-merchant",
        )

        category = Category.objects.create(
            merchant=cls.merchant,
            name="Electronics",
        )
        other_category = Category.objects.create(
            merchant=cls.other_merchant,
            name="Electronics",
        )

        cls.product = Product.objects.create(
            merchant=cls.merchant,
            category=category,
            name="Laptop",
            sku="LAPTOP-001",
        )
        cls.other_product = Product.objects.create(
            merchant=cls.other_merchant,
            category=other_category,
            name="Phone",
            sku="PHONE-001",
        )
        cls.second_product = Product.objects.create(
            merchant=cls.merchant,
            category=category,
            name="Tablet",
            sku="TABLET-001",
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            name="Black",
            sku="LAPTOP-001-BLACK",
        )
        cls.other_variant = ProductVariant.objects.create(
            product=cls.other_product,
            name="Silver",
            sku="PHONE-001-SILVER",
        )

        cls.inventory = Inventory.objects.create(
            variant=cls.variant,
            quantity=100,
            reserved=20,
        )
        cls.other_inventory = Inventory.objects.create(
            variant=cls.other_variant,
            quantity=50,
            reserved=10,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def post_adjustment(
        self,
        data,
        *,
        product_id=None,
        variant_id=None,
        merchant_id=None,
    ):
        url = reverse(
            "inventory-adjustment",
            kwargs={
                "pk": (self.product.pk if product_id is None else product_id),
                "variant_id": (self.variant.pk if variant_id is None else variant_id),
            },
        )

        if merchant_id is None:
            merchant_id = self.merchant.pk

        return self.client.post(
            f"{url}?merchant_id={merchant_id}",
            data=data,
            content_type="application/json",
        )

    def assert_inventory_unchanged(self):
        self.inventory.refresh_from_db()
        self.other_inventory.refresh_from_db()

        self.assertEqual(self.inventory.quantity, 100)
        self.assertEqual(self.other_inventory.quantity, 50)
        self.assertFalse(AuditLog.objects.exists())

    def test_successful_adjustment_returns_created(self):
        response = self.post_adjustment(
            {
                "quantity_change": 10,
                "reason": "New stock received",
            }
        )

        self.assertEqual(response.status_code, 201)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 110)

        log = AuditLog.objects.get(product=self.product)
        payload = response.json()

        self.assertEqual(payload["id"], log.pk)
        self.assertEqual(payload["actor"], self.user.username)
        self.assertEqual(payload["action"], "inventory.adjusted")
        self.assertEqual(payload["details"], log.details)
        self.assertIn("created_at", payload)

    def test_invalid_adjustment_returns_bad_request(self):
        invalid_requests = (
            {"quantity_change": 0, "reason": "Correction"},
            {"quantity_change": -81, "reason": "Correction"},
            {"quantity_change": 5, "reason": ""},
        )

        for data in invalid_requests:
            with self.subTest(data=data):
                response = self.post_adjustment(data)

                self.assertEqual(response.status_code, 400)
                self.assert_inventory_unchanged()

    def test_unauthenticated_user_cannot_adjust_inventory(self):
        self.client.logout()

        response = self.post_adjustment(
            {
                "quantity_change": 10,
                "reason": "New stock",
            }
        )

        self.assertIn(response.status_code, (401, 403))
        self.assert_inventory_unchanged()

    def test_nonmember_cannot_adjust_merchant_inventory(self):
        response = self.post_adjustment(
            {
                "quantity_change": 10,
                "reason": "New stock",
            },
            merchant_id=self.other_merchant.pk,
            product_id=self.other_product.pk,
            variant_id=self.other_variant.pk,
        )

        self.assertEqual(response.status_code, 404)
        self.assert_inventory_unchanged()

    def test_variant_from_another_merchant_is_rejected(self):
        response = self.post_adjustment(
            {
                "quantity_change": 10,
                "reason": "New stock",
            },
            product_id=self.other_product.pk,
            variant_id=self.other_variant.pk,
        )

        self.assertEqual(response.status_code, 404)
        self.assert_inventory_unchanged()

    def test_variant_from_another_product_is_rejected(self):
        response = self.post_adjustment(
            {
                "quantity_change": 10,
                "reason": "New stock",
            },
            product_id=self.second_product.pk,
        )

        self.assertEqual(response.status_code, 404)
        self.assert_inventory_unchanged()

    def test_invalid_merchant_ids_are_rejected(self):
        for merchant_id in ("", "invalid", "0", "-1"):
            with self.subTest(merchant_id=merchant_id):
                response = self.post_adjustment(
                    {
                        "quantity_change": 10,
                        "reason": "New stock",
                    },
                    merchant_id=merchant_id,
                )

                self.assertEqual(response.status_code, 400)
                self.assertIn("merchant_id", response.json())
                self.assert_inventory_unchanged()

    def test_missing_merchant_id_is_rejected(self):
        response = self.client.post(
            reverse(
                "inventory-adjustment",
                kwargs={
                    "pk": self.product.pk,
                    "variant_id": self.variant.pk,
                },
            ),
            data={
                "quantity_change": 10,
                "reason": "New stock",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("merchant_id", response.json())
        self.assert_inventory_unchanged()

    def test_adjustment_appears_in_product_activity(self):
        response = self.post_adjustment(
            {
                "quantity_change": 10,
                "reason": "New stock",
            }
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.get(
            reverse(
                "product-activity",
                kwargs={"pk": self.product.pk},
            )
            + f"?merchant_id={self.merchant.pk}"
        )

        self.assertEqual(response.status_code, 200)

        results = response.json()["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["action"], "inventory.adjusted")
        self.assertEqual(
            results[0]["details"]["quantity_after"],
            110,
        )

    def test_authenticated_adjustment_requires_csrf(self):
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)

        response = self.post_adjustment(
            {
                "quantity_change": 10,
                "reason": "New stock",
            }
        )

        self.assertEqual(response.status_code, 403)
        self.assert_inventory_unchanged()

    def test_authenticated_adjustment_with_csrf_succeeds(self):
        self.client = Client(enforce_csrf_checks=True)

        page = self.client.get("/login/")
        token = page.cookies["csrftoken"].value

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "inventory-adjustment",
                kwargs={
                    "pk": self.product.pk,
                    "variant_id": self.variant.pk,
                },
            )
            + f"?merchant_id={self.merchant.pk}",
            data={
                "quantity_change": 10,
                "reason": "New stock",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 201)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 110)

        log = AuditLog.objects.get(product=self.product)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.action, "inventory.adjusted")
