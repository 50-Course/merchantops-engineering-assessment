from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from catalog.models import Category, Merchant, Product


class DemoAuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="demo_operator",
            password="test-password-123",
        )

        cls.merchant = Merchant.objects.create(
            name="Northstar Retail",
            slug="demo-auth-northstar",
        )
        cls.merchant.members.add(cls.user)

        category = Category.objects.create(
            merchant=cls.merchant,
            name="Computers",
        )

        cls.product = Product.objects.create(
            merchant=cls.merchant,
            category=category,
            name="Test Laptop",
            sku="DEMO-AUTH-001",
        )

    def setUp(self):
        # Enforce real CSRF checks for this test class.
        self.client = Client(enforce_csrf_checks=True)

    def test_login_page_sets_csrf_cookie(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_valid_login_creates_session(self):
        page = self.client.get("/login/")
        token = page.cookies["csrftoken"].value

        response = self.client.post(
            "/login/",
            {
                "username": "demo_operator",
                "password": "test-password-123",
                "csrfmiddlewaretoken": token,
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("sessionid", response.cookies)

        products = self.client.get(
            reverse("product-list"),
            {"merchant_id": self.merchant.pk},
        )

        self.assertEqual(products.status_code, 200)
        self.assertEqual(products.data["count"], 1)

    def test_login_rejects_missing_csrf(self):
        response = self.client.post(
            "/login/",
            {
                "username": "demo_operator",
                "password": "test-password-123",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_invalid_credentials_do_not_authenticate(self):
        page = self.client.get("/login/")
        token = page.cookies["csrftoken"].value

        response = self.client.post(
            "/login/",
            {
                "username": "demo_operator",
                "password": "incorrect-password",
                "csrfmiddlewaretoken": token,
            },
        )

        self.assertEqual(response.status_code, 200)

        products = self.client.get(
            reverse("product-list"),
            {"merchant_id": self.merchant.pk},
        )

        self.assertIn(products.status_code, (401, 403))

    def test_authenticated_patch_requires_csrf(self):
        self.client.force_login(self.user)

        response = self.client.patch(
            reverse(
                "product-detail",
                kwargs={"pk": self.product.pk},
            )
            + f"?merchant_id={self.merchant.pk}",
            data='{"name":"Unauthorized Change"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Test Laptop")

    def test_authenticated_patch_with_csrf_succeeds(self):
        page = self.client.get("/login/")
        token = page.cookies["csrftoken"].value

        self.client.force_login(self.user)

        # Session authentication must not bypass CSRF.
        response = self.client.patch(
            reverse(
                "product-detail",
                kwargs={"pk": self.product.pk},
            )
            + f"?merchant_id={self.merchant.pk}",
            data='{"name":"Updated Laptop"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 200)

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Updated Laptop")
