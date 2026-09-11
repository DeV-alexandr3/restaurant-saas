from django.contrib import admin
from .models import (
    Category,
    Product, 
    ProductVariation,
    AddonGroup,
    Addon,
    Order,
    OrderItem,
    OrderItemAddon,
    )

admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderItemAddon)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "restaurant",
        "position",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "restaurant__name",
    )

    list_filter = (
        "restaurant",
        "is_active",
    )

    ordering = (
        "restaurant",
        "position",
        "name",
    )

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "restaurant",
        "category",
        "price",
        "is_available",
        "created_at",
    )

    search_fields = (
        "name",
        "restaurant__name",
        "category__name",
    )

    list_filter = (
        "restaurant",
        "category",
        "is_available",
    )

@admin.register(ProductVariation)
class ProductVariationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "name",
        "price",
        "position",
        "is_available",
        "created_at",
    )

    search_fields = (
        "product__name",
        "name",
    )

    list_filter = (
        "is_available",
        "product",
    )

    ordering = (
        "product",
        "position",
        "name",
    )
    
@admin.register(AddonGroup)
class AddonGroupAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "name",
        "min_choices",
        "max_choices",
        "position",
        "is_active",
    )

    search_fields = (
        "product__name",
        "name",
    )

    list_filter = (
        "is_active",
        "product",
    )


@admin.register(Addon)
class AddonAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "group",
        "name",
        "price",
        "position",
        "is_available",
    )

    search_fields = (
        "group__name",
        "name",
    )

    list_filter = (
        "is_available",
        "group",
    )
