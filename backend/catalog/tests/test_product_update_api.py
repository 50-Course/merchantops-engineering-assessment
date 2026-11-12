from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Merchant, Product


class ProductUpdateAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="product-editor",
            password="test-password",
        )

        cls.merchant = Merchant.objects.create(
            name="Northstar",
            slug="update-northstar",
        )
        cls.other_merchant = Merchant.objects.create(
            name="Summit",
            slug="update-summit",
        )
        cls.merchant.members.add(cls.user)

        cls.category = Category.objects.create(
            merchant=cls.merchant,
            name="Computers",
        )
        cls.other_category = Category.objects.create(
            merchant=cls.other_merchant,
            name="Private Category",
        )

        cls.product = Product.objects.create(
            merchant=cls.merchant,
            category=cls.category,
            name="Workstation",
            sku="WS-001",
            status=Product.Status.DRAFT,
        )

        cls.other_product = Product.objects.create(
            merchant=cls.other_merchant,
            category=cls.other_category,
            name="Private Workstation",
            sku="PRIVATE-WS-001",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def url(self, product):
        return reverse(
            "product-detail",
            kwargs={"pk": product.pk},
        )

    def test_member_can_update_product(self):
        response = self.client.patch(
            self.url(self.product) + f"?merchant_id={self.merchant.pk}",
            data={
                "name": "Updated Workstation",
                "description": "Updated description",
                "status": Product.Status.ACTIVE,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.name,
            "Updated Workstation",
        )
        self.assertEqual(
            self.product.description,
            "Updated description",
        )
        self.assertEqual(
            self.product.status,
            Product.Status.ACTIVE,
        )

    def test_cannot_update_other_merchant_product(self):
        response = self.client.patch(
            self.url(self.other_product) + f"?merchant_id={self.merchant.pk}",
            data={"name": "Tampered"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

        self.other_product.refresh_from_db()

        self.assertEqual(
            self.other_product.name,
            "Private Workstation",
        )

    def test_cannot_assign_other_merchant_category(self):
        response = self.client.patch(
            self.url(self.product) + f"?merchant_id={self.merchant.pk}",
            data={"category": self.other_category.pk},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.category_id,
            self.category.pk,
        )

    def test_cannot_change_product_merchant(self):
        response = self.client.patch(
            self.url(self.product) + f"?merchant_id={self.merchant.pk}",
            data={"merchant": self.other_merchant.pk},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.merchant_id,
            self.merchant.pk,
        )

    def test_unauthenticated_update_rejected(self):
        self.client.logout()

        response = self.client.patch(
            self.url(self.product) + f"?merchant_id={self.merchant.pk}",
            data={"name": "Unauthorized"},
            content_type="application/json",
        )

        self.assertIn(response.status_code, (401, 403))

    def test_missing_merchant_context_rejected(self):
        response = self.client.patch(
            self.url(self.product),
            data={"name": "Updated"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_duplicate_merchant_sku_returns_validation_error(self):
        other = Product.objects.create(
            merchant=self.merchant,
            category=self.category,
            name="Existing Product",
            sku="ALREADY-USED",
        )

        response = self.client.patch(
            self.url(self.product) + f"?merchant_id={self.merchant.pk}",
            data={"sku": other.sku},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        self.product.refresh_from_db()
        self.assertEqual(self.product.sku, "WS-001")
