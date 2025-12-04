from django.core.management.base import BaseCommand
from core.models import Currency

class Command(BaseCommand):
    help = "Seed default currencies"

    def handle(self, *args, **kwargs):
        data = [
            ("KES", "Kenyan Shilling"),
            ("USD", "US Dollar"),
            ("EUR", "Euro"),
            ("ETH", "Ethereum"),
            ("ZAR", "South African Rand"),
            ("TZS", "Tanzanian Shilling"),
            ("UGX", "Ugandan Shilling"),
        ]

        for code, name in data:
            currency, created = Currency.objects.get_or_create(
                code=code, defaults={'name': name, 'is_active': True}
            )
            if not created:
                # Ensure existing currencies are active
                currency.name = name
                currency.is_active = True
                currency.save()

        self.stdout.write(self.style.SUCCESS("Currencies seeded successfully!"))
