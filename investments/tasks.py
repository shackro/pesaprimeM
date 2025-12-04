from decimal import Decimal
from django.utils import timezone
from investments.models import Asset
import requests

def fetch_prices():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price", params={
            "ids": "bitcoin,ethereum,binancecoin,solana,ripple,cardano,dogecoin,polkadot",
            "vs_currencies": "usd"
        })
        data = response.json()

        return {
            'BTC': Decimal(str(data['bitcoin']['usd'])),
            'ETH': Decimal(str(data['ethereum']['usd'])),
            'BNB': Decimal(str(data['binancecoin']['usd'])),
            'SOL': Decimal(str(data['solana']['usd'])),
            'XRP': Decimal(str(data['ripple']['usd'])),
            'ADA': Decimal(str(data['cardano']['usd'])),
            'DOGE': Decimal(str(data['dogecoin']['usd'])),
            'DOT': Decimal(str(data['polkadot']['usd'])),
        }
    except Exception as e:
        print("Price API failed:", e)
        return {}

def update_assets_prices():
    print("Running scheduled price update...")

    prices = fetch_prices()
    if not prices:
        print("No prices returned.")
        return

    for symbol, price in prices.items():
        asset = Asset.objects.filter(symbol=symbol).first()
        if asset:
            asset.current_price = price
            asset.last_updated = timezone.now()
            asset.save()

    print("Prices updated successfully!")
