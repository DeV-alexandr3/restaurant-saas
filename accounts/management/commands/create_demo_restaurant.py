import os

from django.core.management.base import BaseCommand

from accounts.models import User
from restaurants.models import Restaurant, RestaurantMember


class Command(BaseCommand):
    help = "Cria restaurante de teste e vincula o administrador"

    def handle(self, *args, **options):

        admin_email = os.getenv("ADMIN_EMAIL")

        if not admin_email:
            self.stdout.write(
                self.style.ERROR(
                    "ADMIN_EMAIL não configurado."
                )
            )
            return

        user = User.objects.filter(
            email=admin_email
        ).first()

        if not user:
            self.stdout.write(
                self.style.ERROR(
                    "Administrador não encontrado."
                )
            )
            return

        restaurant, created = Restaurant.objects.get_or_create(
            slug="pizzaria-napoli",
            defaults={
                "name": "Pizzaria Napoli",
                "phone": "",
                "is_active": True,
                "primary_color": "#111827",
                "background_color": "#f6f7f9",
                "accepts_pickup": True,
                "accepts_delivery": True,
                "accepts_table_orders": True,
                "minimum_order": 0,
                "delivery_fee": 0,
                "estimated_time_minutes": 30,
            },
        )

        membership, membership_created = RestaurantMember.objects.get_or_create(
            user=user,
            restaurant=restaurant,
            defaults={
                "role": "ADMIN",
                "is_active": True,
            },
        )

        # Garante que o vínculo fique como ADMIN e ativo
        if membership.role != "ADMIN" or not membership.is_active:
            membership.role = "ADMIN"
            membership.is_active = True
            membership.save(
                update_fields=[
                    "role",
                    "is_active",
                ]
            )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    "Restaurante criado com sucesso."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Restaurante já existia."
                )
            )

        if membership_created:
            self.stdout.write(
                self.style.SUCCESS(
                    "Administrador vinculado ao restaurante."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Vínculo do administrador confirmado."
                )
            )