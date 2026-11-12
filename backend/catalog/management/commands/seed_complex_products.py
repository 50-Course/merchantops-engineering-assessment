from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Inventory, PriceRule, Product, ProductVariant

COMPLEX_VARIANT_TARGETS = {
    "ASSESS-000001": 50,
    "ASSESS-000002": 50,
    "ASSESS-000003": 25,
    "ASSESS-000004": 25,
}


def verify_complete_enrichment():
    """Reject incomplete or inconsistent complex-product fixtures."""

    for sku, target in COMPLEX_VARIANT_TARGETS.items():
        product = Product.objects.get(sku=sku)

        variants = list(ProductVariant.objects.filter(product=product))

        expected_skus = {f"{sku}-V{number}" for number in range(1, target + 1)}

        if (
            len(variants) != target
            or {variant.sku for variant in variants} != expected_skus
        ):
            raise CommandError(f"Inconsistent complex variants for {sku}.")

        for variant in variants:
            if not variant.sku.startswith(f"{sku}-V"):
                raise CommandError("Unexpected variant SKU.")

            # Standard variants are managed by the base seeder.
            if variant.sku in (f"{sku}-V1", f"{sku}-V2"):
                continue

            tiers = sorted(
                PriceRule.objects.filter(variant=variant).values_list("tier", flat=True)
            )

            if tiers != ["retail", "wholesale"]:
                raise CommandError(f"Incomplete prices for {variant.sku}.")

            if Inventory.objects.filter(variant=variant).count() != 1:
                raise CommandError(f"Incomplete inventory for {variant.sku}.")


class Command(BaseCommand):
    help = "Add deterministic complex products to the seeded catalogue."

    @transaction.atomic
    def handle(self, *args, **options):
        products = {}

        for sku in COMPLEX_VARIANT_TARGETS:
            try:
                products[sku] = Product.objects.select_for_update().get(sku=sku)
            except Product.DoesNotExist:
                raise CommandError(f"Missing {sku}. Run seed_catalog first.")
            except Product.MultipleObjectsReturned:
                raise CommandError(f"Ambiguous product SKU: {sku}")

        states = []

        for sku, target in COMPLEX_VARIANT_TARGETS.items():
            existing = list(
                ProductVariant.objects.filter(product=products[sku]).values_list(
                    "sku", flat=True
                )
            )

            standard = {f"{sku}-V1", f"{sku}-V2"}
            complete = {f"{sku}-V{number}" for number in range(1, target + 1)}

            if len(existing) == 2 and set(existing) == standard:
                states.append("standard")
            elif len(existing) == target and set(existing) == complete:
                states.append("enriched")
            else:
                raise CommandError(
                    f"Partial or unexpected fixture for {sku}. " "No changes made."
                )

        if all(state == "enriched" for state in states):
            verify_complete_enrichment()
            self.stdout.write(
                self.style.SUCCESS("Complex products already seeded. No changes made.")
            )
            return

        if not all(state == "standard" for state in states):
            raise CommandError("Mixed enrichment state. Refusing to modify catalogue.")

        additional = []

        for sku, target in COMPLEX_VARIANT_TARGETS.items():
            for number in range(3, target + 1):
                additional.append(
                    ProductVariant(
                        product=products[sku],
                        sku=f"{sku}-V{number}",
                        name=f"Variant {number}",
                    )
                )

        ProductVariant.objects.bulk_create(
            additional,
            batch_size=500,
        )

        created = list(
            ProductVariant.objects.filter(product__in=products.values()).exclude(
                sku__in=[
                    f"{sku}-V{number}"
                    for sku in COMPLEX_VARIANT_TARGETS
                    for number in (1, 2)
                ]
            )
        )

        if len(created) != 142:
            raise CommandError(
                "Expected 142 additional variants. " "Transaction will roll back."
            )

        PriceRule.objects.bulk_create(
            [
                PriceRule(
                    variant=variant,
                    tier=tier,
                    amount=Decimal("99.00"),
                )
                for variant in created
                for tier in ("retail", "wholesale")
            ],
            batch_size=500,
        )

        Inventory.objects.bulk_create(
            [
                Inventory(
                    variant=variant,
                    quantity=100,
                    reserved=10,
                )
                for variant in created
            ],
            batch_size=500,
        )

        verify_complete_enrichment()

        self.stdout.write(
            self.style.SUCCESS(
                "Created 142 additional variants, "
                "284 prices and 142 inventory records."
            )
        )
