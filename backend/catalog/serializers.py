import re

from django.db import connection, transaction
from rest_framework import serializers

from catalog.models import AuditLog, Category, Inventory, Product


class ProductListSerializer(serializers.ModelSerializer):
    category = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "status",
            "category",
            "image_url",
        ]


class ProductUpdateSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "description",
            "status",
            "category",
            "image_url",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        allowed = set(self.fields)
        unexpected = set(self.initial_data) - allowed

        # Read-only fields must not be submitted either.
        unexpected |= set(self.initial_data) & {"id"}

        if unexpected:
            raise serializers.ValidationError(
                {
                    field: "This field cannot be modified."
                    for field in sorted(unexpected)
                }
            )

        return attrs

    def validate_sku(self, value):
        product = self.instance

        duplicates = Product.objects.filter(
            merchant_id=product.merchant_id,
            sku=value,
        ).exclude(pk=product.pk)

        if duplicates.exists():
            raise serializers.ValidationError(
                "A product with this SKU already exists " "for this merchant."
            )

        return value

    def validate_category(self, category):
        if category.merchant_id != self.instance.merchant_id:
            raise serializers.ValidationError(
                "Category does not belong to this merchant."
            )

        return category

    def validate_image_url(self, value):
        if value and not re.fullmatch(
            r"/product-images/[a-z0-9][a-z0-9_-]*\.webp",
            value,
        ):
            raise serializers.ValidationError(
                "Expected a local /product-images/*.webp path."
            )

        return value


class ProductActivitySerializer(serializers.ModelSerializer):
    actor = serializers.CharField(
        source="actor.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "action",
            "details",
            "created_at",
        ]


class InventoryAdjustmentSerializer(serializers.Serializer):
    quantity_change = serializers.IntegerField()
    reason = serializers.CharField()

    def validate(self, attrs):
        unexpected = set(self.initial_data) - set(self.fields)

        if unexpected:
            raise serializers.ValidationError(
                {
                    field: "This field cannot be modified."
                    for field in sorted(unexpected)
                }
            )

        return attrs

    def validate_quantity_change(self, value):
        if type(self.initial_data["quantity_change"]) is not int:
            raise serializers.ValidationError("Quantity change must be an integer.")

        if value == 0:
            raise serializers.ValidationError("Quantity change must be nonzero.")

        return value

    @transaction.atomic
    def create(self, validated_data):
        variant = validated_data["variant"]
        actor = validated_data["actor"]
        quantity_change = validated_data["quantity_change"]
        reason = validated_data["reason"]

        try:
            inventory = Inventory.objects.select_for_update().get(
                variant_id=variant.pk,
            )
        except Inventory.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"inventory": "This variant has no inventory record."}
            ) from exc

        quantity_before = inventory.quantity
        quantity_after = quantity_before + quantity_change

        if quantity_after < inventory.reserved:
            raise serializers.ValidationError(
                {
                    "quantity_change": (
                        "Stock quantity cannot be less than " "reserved inventory."
                    )
                }
            )

        _, max_quantity = connection.ops.integer_field_range(
            Inventory._meta.get_field("quantity").get_internal_type()
        )

        if max_quantity is not None and quantity_after > max_quantity:
            raise serializers.ValidationError(
                {
                    "quantity_change": (
                        "The resulting stock quantity exceeds "
                        "the maximum supported quantity."
                    )
                }
            )

        inventory.quantity = quantity_after
        inventory.save(update_fields=["quantity"])

        return AuditLog.objects.create(
            product_id=variant.product_id,
            actor=actor,
            action="inventory.adjusted",
            details={
                "variant_id": variant.pk,
                "actor_id": actor.pk,
                "actor_username": actor.get_username(),
                "quantity_change": quantity_change,
                "quantity_before": quantity_before,
                "quantity_after": quantity_after,
                "reserved": inventory.reserved,
                "reason": reason,
            },
        )
