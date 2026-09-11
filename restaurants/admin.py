from django.contrib import admin
from .models import Restaurant, RestaurantMember


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "phone",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "slug",
        "phone",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    prepopulated_fields = {
        "slug": ("name",)
    }

@admin.register(RestaurantMember)
class RestaurantMemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "restaurant",
        "role",
        "is_active",
        "created_at",
    )

    search_fields = (
        "user__email",
        "restaurant__name",
    )

    list_filter = (
        "role",
        "is_active",
        "restaurant",
    )