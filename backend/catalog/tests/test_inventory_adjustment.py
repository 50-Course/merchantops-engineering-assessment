from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from rest_framework.exceptions import ValidationError

from catalog.models import (
    AuditLog,
    Category,
    Inventory,
    Merchant,
    Product,
    ProductVariant,
)
from catalog.serializers import InventoryAdjustmentSerializer


class InventoryAdjustmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="inventory-operator",
            password="test-password",
        )
        cls.merchant = Merchant.objects.create(
            name="Inventory Merchant",
            slug="inventory-merchant",
        )
        cls.merchant.members.add(cls.user)

        category = Category.objects.create(
            merchant=cls.merchant,
            name="Electronics",
        )
        cls.product = Product.objects.create(
            merchant=cls.merchant,
            category=category,
            name="Laptop",
            sku="LAPTOP-001",
        )
        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            name="Black",
            sku="LAPTOP-001-BLACK",
        )
        cls.inventory = Inventory.objects.create(
            variant=cls.variant,
            quantity=100,
            reserved=20,
        )

    def adjust_inventory(self, quantity_change, reason="Stock correction"):
        serializer = InventoryAdjustmentSerializer(
            data={
                "quantity_change": quantity_change,
                "reason": reason,
            }
        )
        serializer.is_valid(raise_exception=True)

        return serializer.save(
            variant=self.variant,
            actor=self.user,
        )

    def assert_inventory_unchanged(self):
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 100)
        self.assertEqual(self.inventory.reserved, 20)
        self.assertFalse(AuditLog.objects.filter(product=self.product).exists())

    def test_positive_adjustment_increases_stock(self):
        self.adjust_inventory(10)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 110)
        self.assertEqual(self.inventory.reserved, 20)

    def test_negative_adjustment_decreases_stock(self):
        self.adjust_inventory(-10)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 90)
        self.assertEqual(self.inventory.reserved, 20)

    def test_adjustment_to_reserved_quantity_is_allowed(self):
        self.adjust_inventory(-80)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 20)
        self.assertEqual(self.inventory.reserved, 20)

    def test_adjustment_below_reserved_quantity_is_rejected(self):
        with self.assertRaises(ValidationError) as error:
            self.adjust_inventory(-81)

        self.assertIn("quantity_change", error.exception.detail)
        self.assert_inventory_unchanged()

    def test_invalid_quantity_changes_are_rejected(self):
        invalid_values = (
            0,
            1.5,
            -1.5,
            5.0,
            "5",
            True,
            False,
            None,
        )

        for value in invalid_values:
            with self.subTest(quantity_change=value):
                serializer = InventoryAdjustmentSerializer(
                    data={
                        "quantity_change": value,
                        "reason": "Stock correction",
                    }
                )

                self.assertFalse(serializer.is_valid())
                self.assertIn("quantity_change", serializer.errors)

        self.assert_inventory_unchanged()

    def test_missing_quantity_change_is_rejected(self):
        serializer = InventoryAdjustmentSerializer(data={"reason": "Stock correction"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("quantity_change", serializer.errors)

    def test_invalid_reasons_are_rejected(self):
        for reason in ("", "   ", None):
            with self.subTest(reason=reason):
                serializer = InventoryAdjustmentSerializer(
                    data={
                        "quantity_change": 5,
                        "reason": reason,
                    }
                )

                self.assertFalse(serializer.is_valid())
                self.assertIn("reason", serializer.errors)

        self.assert_inventory_unchanged()

    def test_missing_reason_is_rejected(self):
        serializer = InventoryAdjustmentSerializer(data={"quantity_change": 5})

        self.assertFalse(serializer.is_valid())
        self.assertIn("reason", serializer.errors)

    def test_unexpected_fields_are_rejected(self):
        for field in ("quantity", "reserved", "actor", "variant_id"):
            with self.subTest(field=field):
                serializer = InventoryAdjustmentSerializer(
                    data={
                        "quantity_change": 5,
                        "reason": "Stock correction",
                        field: 999,
                    }
                )

                self.assertFalse(serializer.is_valid())
                self.assertIn(field, serializer.errors)

    def test_adjustment_exceeding_maximum_quantity_is_rejected(self):
        _, max_quantity = connection.ops.integer_field_range(
            Inventory._meta.get_field("quantity").get_internal_type()
        )

        with self.assertRaises(ValidationError) as error:
            self.adjust_inventory(max_quantity)

        self.assertIn("quantity_change", error.exception.detail)
        self.assert_inventory_unchanged()

    def test_missing_inventory_is_rejected(self):
        self.inventory.delete()

        with self.assertRaises(ValidationError) as error:
            self.adjust_inventory(5)

        self.assertIn("inventory", error.exception.detail)
        self.assertFalse(Inventory.objects.filter(variant=self.variant).exists())
        self.assertFalse(AuditLog.objects.filter(product=self.product).exists())

    def test_successful_adjustment_creates_accurate_audit(self):
        self.adjust_inventory(-5, reason="Damaged stock")

        log = AuditLog.objects.get(product=self.product)

        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.action, "inventory.adjusted")
        self.assertIsNotNone(log.created_at)
        self.assertEqual(
            log.details,
            {
                "variant_id": self.variant.pk,
                "actor_id": self.user.pk,
                "actor_username": self.user.get_username(),
                "quantity_change": -5,
                "quantity_before": 100,
                "quantity_after": 95,
                "reserved": 20,
                "reason": "Damaged stock",
            },
        )

    def test_audit_failure_rolls_back_inventory_update(self):
        with patch(
            "catalog.serializers.AuditLog.objects.create",
            side_effect=IntegrityError("Audit creation failed"),
        ):
            with self.assertRaises(IntegrityError):
                self.adjust_inventory(10)

        self.assert_inventory_unchanged()


@skipUnlessDBFeature("has_select_for_update")
class InventoryAdjustmentConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.first_operator = get_user_model().objects.create_user(
            username="first-operator",
        )
        self.second_operator = get_user_model().objects.create_user(
            username="second-operator",
        )

        merchant = Merchant.objects.create(
            name="Concurrency Merchant",
            slug="concurrency-merchant",
        )
        merchant.members.add(
            self.first_operator,
            self.second_operator,
        )

        category = Category.objects.create(
            merchant=merchant,
            name="Electronics",
        )
        self.product = Product.objects.create(
            merchant=merchant,
            category=category,
            name="Laptop",
            sku="LAPTOP-001",
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="Black",
            sku="LAPTOP-001-BLACK",
        )
        self.inventory = Inventory.objects.create(
            variant=self.variant,
            quantity=100,
            reserved=20,
        )

    def run_competing_adjustments(self, first_change, second_change):
        barrier = Barrier(2)

        def adjust(actor, quantity_change):
            close_old_connections()

            try:
                serializer = InventoryAdjustmentSerializer(
                    data={
                        "quantity_change": quantity_change,
                        "reason": "Stock correction",
                    }
                )
                serializer.is_valid(raise_exception=True)

                barrier.wait(timeout=10)

                try:
                    serializer.save(
                        variant=self.variant,
                        actor=actor,
                    )
                except ValidationError as exc:
                    if "quantity_change" not in exc.detail:
                        raise

                    return False

                return True
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(
                adjust,
                self.first_operator,
                first_change,
            )
            second = executor.submit(
                adjust,
                self.second_operator,
                second_change,
            )

            return [
                first.result(timeout=30),
                second.result(timeout=30),
            ]

    def test_competing_adjustments_preserve_stock_and_audit_history(self):
        results = self.run_competing_adjustments(10, -5)

        self.assertEqual(results, [True, True])

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 105)

        logs = list(
            AuditLog.objects.filter(
                product=self.product,
                action="inventory.adjusted",
            ).order_by("id")
        )

        self.assertEqual(len(logs), 2)

        first, second = logs

        self.assertEqual(first.details["quantity_before"], 100)
        self.assertEqual(
            second.details["quantity_before"],
            first.details["quantity_after"],
        )
        self.assertEqual(second.details["quantity_after"], 105)

        self.assertCountEqual(
            [
                (
                    log.actor_id,
                    log.details["quantity_change"],
                )
                for log in logs
            ],
            [
                (self.first_operator.pk, 10),
                (self.second_operator.pk, -5),
            ],
        )

    def test_competing_deductions_cannot_reduce_stock_below_reserved(self):
        results = self.run_competing_adjustments(-60, -50)

        self.assertCountEqual(results, [True, False])

        self.inventory.refresh_from_db()
        self.assertIn(self.inventory.quantity, (40, 50))
        self.assertEqual(self.inventory.reserved, 20)

        log = AuditLog.objects.get(
            product=self.product,
            action="inventory.adjusted",
        )

        self.assertEqual(log.details["quantity_before"], 100)
        self.assertEqual(
            log.details["quantity_after"],
            self.inventory.quantity,
        )
