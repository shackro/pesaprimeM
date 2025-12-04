from django.core.management.base import BaseCommand
from investments.models import Asset
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seed initial data for the application'

    def handle(self, *args, **kwargs):
        # Create sample assets
        assets_data = [
            {
                'name': 'Bitcoin',
                'symbol': 'BTC',
                'asset_type': 'crypto',
                'current_price': Decimal('92036.00'),
                'change_percentage': Decimal('2.34'),
                'moving_average': Decimal('91000.50'),
                'trend': 'up',
                'min_investment': Decimal('700'),
                'hourly_income': Decimal('160'),
                'duration': 24,
                'roi_percentage': Decimal('15.0'),
                'chart_url': 'https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT'
            },
            {
                'name': 'Ethereum',
                'symbol': 'ETH',
                'asset_type': 'crypto',
                'current_price': Decimal('3016.97'),
                'change_percentage': Decimal('1.23'),
                'moving_average': Decimal('2980.20'),
                'trend': 'up',
                'min_investment': Decimal('600'),
                'hourly_income': Decimal('140'),
                'duration': 24,
                'roi_percentage': Decimal('12.5'),
                'chart_url': 'https://www.tradingview.com/chart/?symbol=BINANCE:ETHUSDT'
            },
            # Add more assets as needed
        ]

        for asset_data in assets_data:
            Asset.objects.get_or_create(
                name=asset_data['name'],
                defaults=asset_data
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded initial data'))