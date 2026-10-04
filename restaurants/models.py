from django.db import models
from cloudinary.models import CloudinaryField
from django.core.validators import RegexValidator


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

        # ---------- Personalização visual ----------

    title_color = models.CharField(
        max_length=7,
        default="#D22A2A",
        verbose_name="Cor dos títulos",
    )

    text_color = models.CharField(
        max_length=7,
        default="#1F2937",
        verbose_name="Cor do texto",
    )

    card_bg_color = models.CharField(
        max_length=7,
        default="#FFF9F2",
        verbose_name="Cor de fundo dos cards",
    )

    title_font = models.CharField(
        max_length=100,
        default="Playfair Display",
        blank=True,
        verbose_name="Fonte dos títulos",
    )

    body_font = models.CharField(
        max_length=100,
        default="Poppins",
        blank=True,
        verbose_name="Fonte do corpo",
    )

    restaurant_name_font = models.CharField(
        max_length=100,
        default="Playfair Display",
        blank=True,
        verbose_name="Fonte do nome do restaurante",
    )

    shortcut_bg_color = models.CharField(
        max_length=30,
        default="rgba(255, 255, 255, 0.05)",
        verbose_name="Cor de fundo dos atalhos de categoria",
    )

    restaurant_name_italic = models.BooleanField(
        default=True,
        verbose_name="Nome do restaurante em itálico",
    )

    product_detail_bg = models.CharField(
        max_length=30,
        default="#FFFFFF",
        verbose_name="Cor de fundo da página de produto",
    )

    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="WhatsApp do restaurante",
        help_text="Formato: 5564999999999 (com código do país e DDD, só números)",
    )

    pix_key = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Chave Pix",
        help_text="CPF, CNPJ, telefone, email ou chave aleatória.",
    )

    pix_qrcode = CloudinaryField(
        "QR Code do Pix",
        blank=True,
        null=True,
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

    def get_google_fonts_url(self):
        """
        Retorna a URL do Google Fonts carregando apenas
        as fontes configuradas para este restaurante.
        """
        fonts = set()

        if self.restaurant_name_font:
            fonts.add(
                f"family={self.restaurant_name_font.replace(' ', '+')}:ital,wght@0,400;0,700;1,400;1,700"
            )

        if self.title_font:
            fonts.add(
                f"family={self.title_font.replace(' ', '+')}:ital,wght@0,400;0,700;1,400;1,700"
            )

        if self.body_font and self.body_font != self.title_font:
            fonts.add(
                f"family={self.body_font.replace(' ', '+')}:wght@400;500;600;700"
            )

        if not fonts:
            return None

        return (
            "https://fonts.googleapis.com/css2?"
            + "&".join(fonts)
            + "&display=swap"
        )

    def get_css_variables(self):
        """
        Retorna o bloco de variáveis CSS que será injetado no template público.
        """
        return (
            f"--restaurant-primary: {self.primary_color};\n"
            f"--restaurant-background: {self.background_color};\n"
            f"--restaurant-title-color: {self.title_color};\n"
            f"--restaurant-text-color: {self.text_color};\n"
            f"--restaurant-card-bg: {self.card_bg_color};\n"
             f"--restaurant-product-detail-bg: {self.product_detail_bg};\n"
            f"--restaurant-shortcut-bg: {self.shortcut_bg_color};\n"
            f"--restaurant-title-font: '{self.title_font}', serif;\n"
            f"--restaurant-body-font: '{self.body_font}', sans-serif;\n"
            f"--restaurant-name-font: '{self.restaurant_name_font}', serif;\n"
            f"--restaurant-name-style: {'italic' if self.restaurant_name_italic else 'normal'};"
        )

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
