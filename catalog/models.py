from django.db import models

from restaurants.models import Restaurant
import uuid


class Category(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="categories",
    )

    name = models.CharField(
        max_length=100
    )

    position = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["position", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "name"],
                name="unique_category_name_per_restaurant",
            )
        ]

    def __str__(self):
        return self.name

class Product(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="products",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )

    name = models.CharField(
        max_length=150
    )

    description = models.TextField(
        blank=True
    )

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    is_available = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class ProductVariation(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variations",
    )

    name = models.CharField(
        max_length=100
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    position = models.PositiveIntegerField(
        default=0
    )

    is_available = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["position", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["product", "name"],
                name="unique_variation_name_per_product",
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"

class AddonGroup(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="addon_groups",
    )

    name = models.CharField(
        max_length=100
    )

    min_choices = models.PositiveIntegerField(
        default=0
    )

    max_choices = models.PositiveIntegerField(
        default=1
    )

    position = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["position", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["product", "name"],
                name="unique_addon_group_name_per_product",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    min_choices__lte=models.F("max_choices")
                ),
                name="addon_group_min_lte_max",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"

class Addon(models.Model):
    group = models.ForeignKey(
        AddonGroup,
        on_delete=models.CASCADE,
        related_name="addons",
    )

    name = models.CharField(
        max_length=100
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    position = models.PositiveIntegerField(
        default=0
    )

    is_available = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["position", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["group", "name"],
                name="unique_addon_name_per_group",
            )
        ]

    def __str__(self):
        return f"{self.group.name} - {self.name}"

class Order(models.Model):
    TYPE_CHOICES = [
        ("pickup", "Retirada"),
        ("delivery", "Entrega"),
        ("table", "Mesa"),
    ]

    STATUS_CHOICES = [
        ("NEW", "Novo"),
        ("CONFIRMED", "Confirmado"),
        ("PREPARING", "Em preparo"),
        ("READY", "Pronto"),
        ("OUT_FOR_DELIVERY", "Saiu para entrega"),
        ("FINISHED", "Finalizado"),
        ("REJECTED", "Recusado"),
        ("CANCELLED", "Cancelado"),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    customer_name = models.CharField(
        max_length=150,
    )

    customer_phone = models.CharField(
        max_length=20,
    )

    order_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="NEW",
    )

    address = models.CharField(
        max_length=255,
        blank=True,
    )

    address_number = models.CharField(
        max_length=20,
        blank=True,
    )

    complement = models.CharField(
        max_length=150,
        blank=True,
    )

    table_number = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    table = models.ForeignKey(
        "restaurants.Table",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    estimated_time_minutes = models.PositiveIntegerField(
        default=30,
    )

    public_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    stock_processed = models.BooleanField(
        default=False,
    )

    notes = models.TextField(
        blank=True,
    )

    def __str__(self):
        return f"Pedido #{self.id} - {self.restaurant.name}"

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    product_name = models.CharField(
        max_length=150,
    )

    variation_name = models.CharField(
        max_length=100,
        blank=True,
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    def __str__(self):
        return f"{self.product_name} - Pedido #{self.order.id}"

class OrderItemAddon(models.Model):
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="addons",
    )

    addon_name = models.CharField(
        max_length=100,
    )

    addon_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    def __str__(self):
        return f"{self.addon_name} - {self.order_item.product_name}"