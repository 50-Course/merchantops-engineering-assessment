from django.core.management import call_command
from django.test import TestCase

from catalog.models import (
    Inventory,
    PriceRule,
    Product,
    ProductVariant,
)


class ComplexCatalogueSeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "seed_catalog",
            products=4,
            seed=42,
            verbosity=0,
        )

    def test_complex_products_have_expected_variant_counts(self):
        call_command("seed_complex_products", verbosity=0)

        expected = {
            "ASSESS-000001": 50,
            "ASSESS-000002": 50,
            "ASSESS-000003": 25,
            "ASSESS-000004": 25,
        }

        for sku, count in expected.items():
            product = Product.objects.get(sku=sku)
            self.assertEqual(product.variants.count(), count)

        self.assertEqual(Product.objects.count(), 4)
        self.assertEqual(ProductVariant.objects.count(), 150)
        self.assertEqual(PriceRule.objects.count(), 300)
        self.assertEqual(Inventory.objects.count(), 150)

    def test_enrichment_is_idempotent(self):
        call_command("seed_complex_products", verbosity=0)
        call_command("seed_complex_products", verbosity=0)

        self.assertEqual(ProductVariant.objects.count(), 150)
        self.assertEqual(PriceRule.objects.count(), 300)
        self.assertEqual(Inventory.objects.count(), 150)

    def test_base_seeder_accepts_enriched_catalogue(self):
        call_command("seed_complex_products", verbosity=0)

        call_command(
            "seed_catalog",
            products=4,
            seed=42,
            verbosity=0,
        )

        self.assertEqual(ProductVariant.objects.count(), 150)

    def test_existing_inventory_is_preserved_on_rerun(self):
        call_command("seed_complex_products", verbosity=0)

        variant = ProductVariant.objects.get(sku="ASSESS-000001-V3")

        inventory = Inventory.objects.get(variant=variant)
        inventory.quantity = 250
        inventory.reserved = 20
        inventory.save()

        call_command("seed_complex_products", verbosity=0)

        inventory.refresh_from_db()

        self.assertEqual(inventory.quantity, 250)
        self.assertEqual(inventory.reserved, 20)
