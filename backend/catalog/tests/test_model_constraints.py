from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from catalog.models import (
    Category,
    Inventory,
    Merchant,
    PriceRule,
    Product,
    ProductVariant,
)


class CatalogConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.merchant = Merchant.objects.create(
            name="Merchant One",
            slug="merchant-one",
        )
        cls.other_merchant = Merchant.objects.create(
            name="Merchant Two",
            slug="merchant-two",
        )
        cls.category = Category.objects.create(
            merchant=cls.merchant,
            name="Electronics",
        )
        cls.other_category = Category.objects.create(
            merchant=cls.other_merchant,
            name="Electronics",
        )
        cls.product = Product.objects.create(
            merchant=cls.merchant,
            category=cls.category,
            name="Laptop",
            sku="LAPTOP-001",
        )
        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="LAPTOP-001-BLACK",
            name="Black",
        )

    def test_product_sku_unique_per_merchant(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.create(
                    merchant=self.merchant,
                    category=self.category,
                    name="Duplicate Laptop",
                    sku="LAPTOP-001",
                )

        other = Product.objects.create(
            merchant=self.other_merchant,
            category=self.other_category,
            name="Another Laptop",
            sku="LAPTOP-001",
        )

        self.assertIsNotNone(other.pk)

    def test_variant_sku_unique_per_product(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductVariant.objects.create(
                    product=self.product,
                    sku="LAPTOP-001-BLACK",
                    name="Duplicate Variant",
                )

    def test_negative_price_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PriceRule.objects.create(
                    variant=self.variant,
                    tier="retail",
                    amount=Decimal("-1.00"),
                )

    def test_reserved_inventory_cannot_exceed_quantity(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Inventory.objects.create(
                    variant=self.variant,
                    quantity=5,
                    reserved=6,
                )

    def test_valid_inventory(self):
        inventory = Inventory.objects.create(
            variant=self.variant,
            quantity=10,
            reserved=3,
        )

        self.assertEqual(inventory.quantity - inventory.reserved, 7)
