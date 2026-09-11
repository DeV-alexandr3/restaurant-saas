import os

from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Cria o administrador inicial do sistema"

    def handle(self, *args, **options):

        email = os.getenv("ADMIN_EMAIL")
        password = os.getenv("ADMIN_PASSWORD")

        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "ADMIN_EMAIL ou ADMIN_PASSWORD não configurados."
                )
            )
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(
                    "Administrador já existe."
                )
            )
            return

        User.objects.create_superuser(
            email=email,
            password=password,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Administrador criado com sucesso."
            )
        )