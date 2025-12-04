import requests
from decimal import Decimal
import random
from datetime import datetime
import yfinance as yf

from django.core.management.base import BaseCommand
from investments.models import Asset

# ---------- HELPERS ----------

def usd_to_kes():
    """Fetch USD → KES conversion rate safely with fallback."""
    try:
        resp = requests.get(
            "https://open.er-api.com/v6/latest/USD",
            timeout=10
        ).json()
        if resp.get("result") != "success":
            raise ValueError("API did not return success")
        rate = resp["rates"]["KES"]
        return Decimal(str(rate))
    except Exception as e:
        print("Error fetching USD/KES rate:", e)
        return Decimal("160")  # fallback

KES_RATE = usd_to_kes()

def randomize_asset_fields(asset):
    """Randomize min investment, hourly income, and duration hours."""
    asset.min_investment = Decimal(random.randint(350, 700))
    asset.hourly_income = Decimal(random.randint(45, 172))
    asset.duration_hours = random.choice([3, 4, 6, 8, 10, 12, 16, 18, 22])
    asset.save()

# ---------- UPDATES ----------

def update_crypto_prices(assets):
    symbol_to_id = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "BNB": "binancecoin",
        "SOL": "solana",
        "XRP": "ripple",
        "ADA": "cardano",
        "DOT": "polkadot",
        "DOGE": "dogecoin",
        "LTC": "litecoin",
        "AVAX": "avalanche-2",
    }

    ids = [symbol_to_id[a.symbol] for a in assets if a.symbol in symbol_to_id]
    if not ids:
        return

    url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=usd"
    try:
        resp = requests.get(url, timeout=10).json()
        for asset in assets:
            cg_id = symbol_to_id.get(asset.symbol)
            if cg_id in resp:
                usd_price = Decimal(resp[cg_id]["usd"])
                kes_price = usd_price * KES_RATE

                asset.change_percentage = (
                    (kes_price - asset.current_price) / asset.current_price * 100
                    if asset.current_price > 0 else 0
                )

                asset.trend = (
                    "up" if asset.change_percentage > 0 else
                    "down" if asset.change_percentage < 0 else
                    "neutral"
                )

                asset.current_price = kes_price
                randomize_asset_fields(asset)

                print(f"[Crypto] {asset.symbol} = {kes_price:.2f} KES | {asset.change_percentage:.2f}%")
    except Exception as e:
        print("Crypto update error:", e)

def update_forex_prices(assets):
    url = "https://api.exchangerate.host/latest?base=USD"
    try:
        resp = requests.get(url, timeout=10).json()
        rates = resp.get("rates", {})

        for asset in assets:
            symbol = asset.symbol
            if symbol == "XAUUSD":  # Gold
                usd_price = Decimal("2000")
            elif "/" in symbol:
                base = symbol[:3]
                quote = symbol[4:]
                rate = rates.get(quote)
                if rate is None:
                    continue
                usd_price = Decimal(rate)
            else:
                continue

            kes_price = usd_price * KES_RATE
            asset.change_percentage = (
                (kes_price - asset.current_price) / asset.current_price * 100
                if asset.current_price > 0 else 0
            )

            asset.trend = (
                "up" if asset.change_percentage > 0 else
                "down" if asset.change_percentage < 0 else
                "neutral"
            )

            asset.current_price = kes_price
            randomize_asset_fields(asset)

            print(f"[Forex] {asset.symbol} = {kes_price:.2f} KES")

    except Exception as e:
        print("Forex update error:", e)

def update_stock_prices(assets):
    for asset in assets:
        try:
            data = yf.Ticker(asset.symbol).history(period="1d")
            if not data.empty:
                usd_price = Decimal(data['Close'].iloc[-1])
                kes_price = usd_price * KES_RATE

                asset.change_percentage = (
                    (kes_price - asset.current_price) / asset.current_price * 100
                    if asset.current_price > 0 else 0
                )

                asset.trend = (
                    "up" if asset.change_percentage > 0 else
                    "down" if asset.change_percentage < 0 else
                    "neutral"
                )

                asset.current_price = kes_price
                randomize_asset_fields(asset)

                print(f"[Stock] {asset.symbol} = {kes_price:.2f} KES")
        except Exception as e:
            print(f"Stock error {asset.symbol}: {e}")

# ---------- DJANGO COMMAND ----------

class Command(BaseCommand):
    help = "Update asset prices (crypto, forex, stocks) with USD→KES conversion."

    def handle(self, *args, **options):
        self.stdout.write("\n========== Updating Prices ==========\n")

        cryptos = Asset.objects.filter(asset_type="crypto", is_active=True)
        forex = Asset.objects.filter(asset_type="forex", is_active=True)
        stocks = Asset.objects.filter(asset_type="stock", is_active=True)

        update_crypto_prices(cryptos)
        update_forex_prices(forex)
        update_stock_prices(stocks)

        self.stdout.write("\n========== Update Complete ==========\n")

# --------------------------------------------------
# MAIN JOB
# --------------------------------------------------
def main():
    print("\n========== Updating Prices ==========\n")

    cryptos = Asset.objects.filter(asset_type="crypto", is_active=True)
    forex = Asset.objects.filter(asset_type="forex", is_active=True)
    stocks = Asset.objects.filter(asset_type="stock", is_active=True)

    update_crypto_prices(cryptos)
    update_forex_prices(forex)
    update_stock_prices(stocks)

    print("\n========== Update Complete ==========\n")


if __name__ == "__main__":
    main()
