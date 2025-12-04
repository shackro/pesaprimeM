from django.core.management.base import BaseCommand
from investments.models import Asset
import uuid
import random

class Command(BaseCommand):
    help = "Create default 24 investment assets (10 crypto, 8 forex, 6 stocks)"

    def handle(self, *args, **kwargs):
        cryptos = [
            ("Bitcoin", "BTC"),
            ("Ethereum", "ETH"),
            ("Binance Coin", "BNB"),
            ("Solana", "SOL"),
            ("Ripple", "XRP"),
            ("Cardano", "ADA"),
            ("Polkadot", "DOT"),
            ("Dogecoin", "DOGE"),
            ("Litecoin", "LTC"),
            ("Avalanche", "AVAX"),
        ]

        forex = [
            ("EUR/USD", "EURUSD"),
            ("USD/JPY", "USDJPY"),
            ("GBP/USD", "GBPUSD"),
            ("USD/CHF", "USDCHF"),
            ("AUD/USD", "AUDUSD"),
            ("NZD/USD", "NZDUSD"),
            ("USD/CAD", "USDCAD"),
            ("Gold Futures", "XAUUSD"),
        ]

        stocks = [
            ("Apple", "AAPL"),
            ("Microsoft", "MSFT"),
            ("Tesla", "TSLA"),
            ("Amazon", "AMZN"),
            ("Google", "GOOGL"),
            ("Meta", "META"),
        ]

        all_assets = [
            ("crypto", cryptos),
            ("forex", forex),
            ("stock", stocks)
        ]

        for asset_type, asset_list in all_assets:
            for name, symbol in asset_list:

                min_invest = random.randint(350, 700)
                hourly = random.randint(45, 172)
                duration_choice = random.choice(Asset.ALLOWED_HOURS)

                obj, created = Asset.objects.update_or_create(
                    symbol=symbol,
                    defaults={
                        "id": uuid.uuid4(),
                        "name": name,
                        "asset_type": asset_type,
                        "current_price": 0,
                        "hourly_income": hourly,
                        "min_investment": min_invest,
                        "duration_hours": duration_choice,
                        "trend": "neutral",
                        "change_percentage": 0,
                        "is_active": True,
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created {name} ({symbol})"))
                else:
                    self.stdout.write(self.style.WARNING(f"Updated {name} ({symbol})"))
