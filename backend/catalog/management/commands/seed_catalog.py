import random
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import (
    Availability,
    Category,
    Inventory,
    Merchant,
    PriceRule,
    Product,
    ProductVariant,
)

IMAGE_NAMES = (
    "laptop",
    "monitor",
    "keyboard",
    "headphones",
    "camera",
    "tablet",
    "smartphone",
    "speaker",
)


class Command(BaseCommand):
    help = "Create deterministic MerchantOps assessment data."

    def add_arguments(self, parser):
        parser.add_argument("--products", type=int, default=5000)
        parser.add_argument("--seed", type=int, default=42)

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["products"]
        seed = options["seed"]

        if count < 2 or count % 2:
            raise CommandError("--products must be an even number >= 2.")

        rng = random.Random(seed)
        slugs = ["assessment-merchant-01", "assessment-merchant-02"]

        existing = list(Merchant.objects.filter(slug__in=slugs))

        if existing:
            if len(existing) != 2:
                raise CommandError("Partial seed detected. Refusing to modify data.")

            merchant_ids = [m.pk for m in existing]
            products = Product.objects.filter(merchant_id__in=merchant_ids)
            variants = ProductVariant.objects.filter(product__in=products)

            counts = {
                "products": products.count(),
                "categories": Category.objects.filter(
                    merchant_id__in=merchant_ids
                ).count(),
                "variants": variants.count(),
                "prices": PriceRule.objects.filter(variant__in=variants).count(),
                "inventory": Inventory.objects.filter(variant__in=variants).count(),
                "availability": Availability.objects.filter(
                    product__in=products
                ).count(),
            }

            expected = {
                "products": count,
                "categories": 16,
                "variants": count * 2,
                "prices": count * 4,
                "inventory": count * 2,
                "availability": count * 2,
            }

            # The optional complex-product fixture adds 142 variants,
            # 284 price rules, and 142 inventory records.
            enriched_expected = {
                **expected,
                "variants": expected["variants"] + 142,
                "prices": expected["prices"] + 284,
                "inventory": expected["inventory"] + 142,
            }

            if counts != expected and counts != enriched_expected:
                raise CommandError(
                    "Existing catalogue differs from requested "
                    "shape. Refusing to overwrite. "
                    f"Existing: {counts}"
                )

            # Counts alone cannot establish that --seed matches
            # the original invocation.
            self.stdout.write(
                self.style.WARNING(
                    "Existing catalogue has matching record counts. "
                    "No changes made. Original seed value "
                    "was not independently verified."
                )
            )
            return

        merchants = [
            Merchant.objects.create(
                name="Northstar Retail",
                slug=slugs[0],
            ),
            Merchant.objects.create(
                name="Summit Supplies",
                slug=slugs[1],
            ),
        ]

        categories = []
        for merchant in merchants:
            for number in range(1, 9):
                categories.append(
                    Category(
                        merchant=merchant,
                        name=f"Category {number:02d}",
                    )
                )
        Category.objects.bulk_create(categories)

        categories = list(
            Category.objects.filter(merchant__slug__in=slugs).order_by(
                "merchant_id", "name"
            )
        )

        category_map = {}
        for category in categories:
            category_map.setdefault(category.merchant_id, []).append(category)

        products = []

        for number in range(1, count + 1):
            merchant = merchants[(number - 1) % 2]
            category = rng.choice(category_map[merchant.pk])

            products.append(
                Product(
                    merchant=merchant,
                    category=category,
                    name=f"Assessment Product {number:06d}",
                    sku=f"ASSESS-{number:06d}",
                    image_url=(
                        "/product-images/"
                        f"{IMAGE_NAMES[(number - 1) % len(IMAGE_NAMES)]}.webp"
                    ),
                    description=(
                        "Standard catalogue product for the "
                        "MerchantOps engineering assessment."
                    ),
                    status=rng.choice(
                        [
                            Product.Status.ACTIVE,
                            Product.Status.ACTIVE,
                            Product.Status.DRAFT,
                        ]
                    ),
                )
            )

        Product.objects.bulk_create(products, batch_size=500)

        products = list(
            Product.objects.filter(merchant__slug__in=slugs).order_by("sku")
        )

        variants = []
        availability = []

        for product in products:
            for variant_number in (1, 2):
                variants.append(
                    ProductVariant(
                        product=product,
                        sku=f"{product.sku}-V{variant_number}",
                        name=f"Variant {variant_number}",
                    )
                )

            for channel in ("online", "retail"):
                availability.append(
                    Availability(
                        product=product,
                        channel=channel,
                        enabled=rng.random() > 0.15,
                    )
                )

        ProductVariant.objects.bulk_create(variants, batch_size=500)

        variants = list(
            ProductVariant.objects.filter(product__merchant__slug__in=slugs).order_by(
                "sku"
            )
        )

        Availability.objects.bulk_create(availability, batch_size=500)

        prices = []
        inventory = []

        for variant in variants:
            base_cents = rng.randint(5000, 500000)

            for tier, multiplier in (
                ("retail", 100),
                ("wholesale", 85),
            ):
                amount = Decimal(base_cents * multiplier) / Decimal(10000)

                prices.append(
                    PriceRule(
                        variant=variant,
                        tier=tier,
                        amount=amount,
                    )
                )

            quantity = rng.randint(0, 500)
            reserved = rng.randint(0, quantity)

            inventory.append(
                Inventory(
                    variant=variant,
                    quantity=quantity,
                    reserved=reserved,
                )
            )

        PriceRule.objects.bulk_create(prices, batch_size=500)
        Inventory.objects.bulk_create(inventory, batch_size=500)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {count} products with seed={seed}. "
                f"Created {len(variants)} variants, "
                f"{len(prices)} prices, "
                f"{len(inventory)} inventory records."
            )
        )
