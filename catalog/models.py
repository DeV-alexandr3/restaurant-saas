from django.db import models

from restaurants.models import Restaurant
import uuid
from cloudinary.models import CloudinaryField


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

    image = CloudinaryField(
        "image",
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

    is_by_weight = models.BooleanField(
        default=False,
        verbose_name="Vendido por peso (kg)",
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

    payment_method = models.CharField(
        max_length=20,
        choices=[
            ("cash", "Dinheiro"),
            ("card", "Cartão"),
            ("pix", "Pix"),
        ],
        default="cash",
        verbose_name="Forma de pagamento",
    )

    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pendente"),
            ("paid", "Pago"),
        ],
        default="pending",
        verbose_name="Status de pagamento",
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

# =========================================================
# COMANDA (PAINEL DO GARÇOM)
# =========================================================

class TableSession(models.Model):
    """
    Comanda de uma mesa. Uma mesa pode ter várias comandas abertas.
    """

    restaurant = models.ForeignKey(
        "restaurants.Restaurant",
        on_delete=models.CASCADE,
        related_name="table_sessions",
    )

    table = models.ForeignKey(
        "restaurants.Table",
        on_delete=models.PROTECT,
        related_name="table_sessions",
    )

    is_open = models.BooleanField(
        default=True,
        verbose_name="Aberta",
    )

    is_paid = models.BooleanField(
        default=False,
        verbose_name="Paga",
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Total",
    )

    opened_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Aberta em",
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fechada em",
    )

    needs_print = models.BooleanField(
        default=True,
        verbose_name="Precisa imprimir",
    )

    printed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Impressa em",
    )

    class Meta:
        verbose_name = "Comanda"
        verbose_name_plural = "Comandas"
        ordering = ["-opened_at"]

    def __str__(self):
        return f"Comanda #{self.id} - Mesa {self.table.number}"

    def recalculate_total(self):
        """Recalcula o total baseado nos itens."""
        from django.db.models import Sum

        total = self.items.aggregate(
            total=Sum("total")
        )["total"] or 0

        self.total = total
        self.save(update_fields=["total"])

        return total


class TableSessionItem(models.Model):
    """
    Item de uma comanda. Guarda snapshot do produto, variação e preço.
    """

    session = models.ForeignKey(
        TableSession,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="session_items",
    )

    product_name = models.CharField(
        max_length=200,
        verbose_name="Nome do produto",
    )

    variation_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Variação",
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Preço unitário",
    )

    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantidade",
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Total",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Observações",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Peso (kg)",
    )

    class Meta:
        verbose_name = "Item da comanda"
        verbose_name_plural = "Itens da comanda"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"


class TableSessionItemAddon(models.Model):
    """
    Adicional de um item da comanda.
    """

    item = models.ForeignKey(
        TableSessionItem,
        on_delete=models.CASCADE,
        related_name="addons",
    )

    addon_name = models.CharField(
        max_length=200,
        verbose_name="Nome do adicional",
    )

    addon_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Preço do adicional",
    )

    class Meta:
        verbose_name = "Adicional do item"
        verbose_name_plural = "Adicionais do item"

    def __str__(self):
        return self.addon_name