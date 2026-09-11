from django.db import models

from restaurants.models import Restaurant
from django.db.models import Sum

class InventoryItem(models.Model):

    UNIT_CHOICES = [
        ("UN", "Unidade"),
        ("KG", "Quilograma"),
        ("G", "Grama"),
        ("L", "Litro"),
        ("ML", "Mililitro"),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )

    name = models.CharField(
        max_length=120
    )

    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default="UN",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )

    minimum_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
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
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "restaurant",
                    "name",
                ],
                name="unique_inventory_item_per_restaurant",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    quantity__gte=0
                ),
                name="inventory_quantity_non_negative",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    minimum_quantity__gte=0
                ),
                name="inventory_minimum_quantity_non_negative",
            ),
        ]
    
    def last_movement(self):
        return self.movements.first()

    def average_unit_cost(self):
        totals = self.movements.filter(
            movement_type="IN",
            total_cost__isnull=False,
            quantity__gt=0,            
        ).filter(
        models.Q(purchase__isnull=True)
        | models.Q(purchase__status="ACTIVE")
        ).aggregate(
            total_quantity=Sum("quantity"),
            total_cost=Sum("total_cost"),
        )

        total_quantity = totals["total_quantity"]
        total_cost = totals["total_cost"]

        if not total_quantity or total_cost is None:
            return None

        return total_cost / total_quantity

    def stock_value(self):
        average_cost = self.average_unit_cost()

        if average_cost is None:
            return None

        return self.quantity * average_cost

    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"

class StockMovement(models.Model):

    TYPE_CHOICES = [
        ("IN", "Entrada"),
        ("OUT", "Saída"),
        ("ADJUST", "Ajuste"),
    ]

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="movements",
    )

    movement_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    reason = models.CharField(
        max_length=255,
        blank=True,
    )

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    supplier = models.CharField(
        max_length=150,
        blank=True,
    )

    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    purchase = models.ForeignKey(
        "Purchase",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    quantity__gte=0
                ),
                name="stock_movement_quantity_non_negative",
            ),

            models.CheckConstraint(
                condition=(
                    models.Q(total_cost__isnull=True)
                    | models.Q(total_cost__gte=0)
                ),
                name="stock_movement_total_cost_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.item.name}"

    def unit_cost(self):

        if (
            self.movement_type == "IN"
            and self.total_cost is not None
            and self.quantity
            and self.quantity > 0
        ):
            return self.total_cost / self.quantity

        return None

class ProductIngredient(models.Model):

    UNIT_CHOICES = [
        ("UN", "Unidade"),
        ("KG", "Quilograma"),
        ("G", "Grama"),
        ("L", "Litro"),
        ("ML", "Mililitro"),
    ]

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="ingredients",
    )

    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="product_ingredients",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default="UN",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "product",
                    "inventory_item",
                ],
                name="unique_product_inventory_item",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    quantity__gt=0
                ),
                name="product_ingredient_quantity_positive",
            ),
        ]

    def __str__(self):
        return (
            f"{self.product.name} - "
            f"{self.inventory_item.name}"
        )

class Purchase(models.Model):
    restaurant = models.ForeignKey(
        "restaurants.Restaurant",
        on_delete=models.PROTECT,
        related_name="purchases",
    )

    supplier = models.CharField(
        max_length=150,
        blank=True,
    )

    purchase_date = models.DateField()

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    STATUS_CHOICES = [
        ("ACTIVE", "Ativa"),
        ("CANCELLED", "Cancelada"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_purchases",
    )

    class Meta:
        ordering = ["-purchase_date", "-created_at"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name="purchase_total_non_negative",
            ),
        ]

    def __str__(self):
        return f"Compra #{self.id} - {self.restaurant.name}"

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="items",
    )

    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="purchase_items",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="purchase_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0),
                name="purchase_item_unit_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name="purchase_item_total_non_negative",
            ),
        ]

    def __str__(self):
        return (
            f"{self.inventory_item.name} "
            f"- Compra #{self.purchase.id}"
        )