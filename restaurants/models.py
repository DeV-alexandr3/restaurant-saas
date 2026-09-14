from django.db import models
from cloudinary.models import CloudinaryField


class Restaurant(models.Model):
    name = models.CharField(max_length=150)

    slug = models.SlugField(
        max_length=160,
        unique=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True
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

    logo = CloudinaryField(
        "logo",
        blank=True,
        null=True,
    )

    banner = CloudinaryField(
        "banner",
        blank=True,
        null=True,
    )

    primary_color = models.CharField(
        max_length=7,
        default="#111827",
    )

    background_color = models.CharField(
        max_length=7,
        default="#f6f7f9",
    )

    accepts_pickup = models.BooleanField(
        default=True,
    )

    accepts_delivery = models.BooleanField(
        default=True,
    )

    accepts_table_orders = models.BooleanField(
        default=True,
    )

    minimum_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    estimated_time_minutes = models.PositiveIntegerField(
        default=30,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    minimum_order__gte=0
                ),
                name="restaurant_minimum_order_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    delivery_fee__gte=0
                ),
                name="restaurant_delivery_fee_non_negative",
            ),
        ]

    def __str__(self):
        return self.name

class RestaurantMember(models.Model):
    ROLE_CHOICES = [
        ("ADMIN", "Administrador"),
        ("EMPLOYEE", "Funcionário"),
    ]

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="restaurant_memberships",
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="members",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="EMPLOYEE",
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "restaurant"],
                name="unique_user_restaurant",
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.restaurant.name}"

class Table(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="tables",
    )

    number = models.PositiveIntegerField()

    name = models.CharField(
        max_length=100,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["number"]

        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "number"],
                name="unique_table_number_per_restaurant",
            )
        ]

    def __str__(self):
        return f"Mesa {self.number} - {self.restaurant.name}"
