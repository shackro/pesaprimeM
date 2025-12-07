import requests
from decimal import Decimal
import random
import yfinance as yf

from investments.models import Asset


API_KEY ="L7SNLCSS0P2WAMDP"
# ---------- HELPERS ----------

def usd_to_kes():
    """Fetch USD → KES conversion rate safely with fallback."""
    try:
        resp = requests.get(
            "https://open.er-api.com/v6/latest/USD",
            timeout=10
        ).json()
        if resp.get("result") != "success":
            raise ValueError("API failed")
        return Decimal(str(resp["rates"]["KES"]))
    except Exception:
        return Decimal("160")  # fallback safe rate

def randomize_asset_fields(asset):
    """Randomize min investment, hourly income, and duration hours."""
    asset.min_investment = Decimal(random.randint(350, 700))
    asset.hourly_income = Decimal(random.randint(45, 172))
    asset.duration_hours = random.choice([3, 4, 6, 8, 10, 12, 16, 18, 22])
    asset.save(update_fields=["min_investment", "hourly_income", "duration_hours"])

# Cache exchange rate at import
KES_RATE = usd_to_kes()

# ---------- UPDATE LOGIC ----------

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

    try:
        resp = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=usd",
            timeout=10
        ).json()

        for asset in assets:
            cg_id = symbol_to_id.get(asset.symbol)
            if cg_id not in resp:
                continue

            usd_price = Decimal(resp[cg_id]["usd"])
            kes_price = usd_price * KES_RATE

            # Percentage change
            old_price = asset.current_price
            asset.change_percentage = (
                (kes_price - old_price) / old_price * 100 if old_price > 0 else 0
            )

            # Trend
            asset.trend = (
                "up" if asset.change_percentage > 0 else
                "down" if asset.change_percentage < 0 else
                "neutral"
            )

            # Update price
            asset.current_price = kes_price
            randomize_asset_fields(asset)

            asset.save(update_fields=[
                "current_price",
                "change_percentage",
                "trend",
                "min_investment",
                "hourly_income",
                "duration_hours"
            ])

    except Exception as e:
        print("Crypto update error:", e)


def update_forex_prices(assets):
    """
    Update forex asset prices using Alpha Vantage.
    Also computes KES value, change percentage, trend, and randomizes fields.
    """
    for asset in assets:
        symbol = asset.symbol.upper()  # e.g., "EURUSD", "GBPUSD", "XAUUSD"

        # Alpha Vantage uses separate symbols for currencies
        from_currency = symbol[:3]
        to_currency = symbol[3:]

        if to_currency != "USD":
            # For now, only support USD as quote currency
            print(f"Skipping {symbol}, only USD quote supported")
            continue

        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_currency}&to_currency={to_currency}&apikey={API_KEY}"

        try:
            resp = requests.get(url, timeout=10).json()
            rate_str = resp.get('Realtime Currency Exchange Rate', {}).get('5. Exchange Rate')

            if not rate_str:
                print(f"No rate returned for {symbol}")
                continue

            usd_price = Decimal(rate_str)
            kes_price = usd_price * KES_RATE

            old_price = asset.current_price or Decimal("0")

            # Compute change percentage
            change_percentage = ((kes_price - old_price) / old_price * 100) if old_price > 0 else 0

            # Determine trend
            trend = "up" if change_percentage > 0 else "down" if change_percentage < 0 else "neutral"

            # Update asset fields
            asset.current_price = kes_price
            asset.change_percentage = change_percentage
            asset.trend = trend

            # Randomize min_investment, hourly_income, duration_hours
            asset.min_investment = Decimal(random.randint(350, 700))
            asset.hourly_income = Decimal(random.randint(45, 172))
            asset.duration_hours = random.choice([3, 4, 6, 8, 10, 12, 16, 18, 22])

            asset.save(update_fields=[
                "current_price", "change_percentage", "trend",
                "min_investment", "hourly_income", "duration_hours"
            ])

        except Exception as e:
            print(f"Forex update error for {symbol}: {e}")


def update_stock_prices(assets):
    for asset in assets:
        try:
            data = yf.Ticker(asset.symbol).history(period="1d")
            if data.empty:
                continue

            usd_price = Decimal(data['Close'].iloc[-1])
            kes_price = usd_price * KES_RATE

            old_price = asset.current_price
            asset.change_percentage = (
                (kes_price - old_price) / old_price * 100 if old_price > 0 else 0
            )

            asset.trend = (
                "up" if asset.change_percentage > 0 else
                "down" if asset.change_percentage < 0 else
                "neutral"
            )

            asset.current_price = kes_price
            randomize_asset_fields(asset)

            asset.save(update_fields=[
                "current_price", "change_percentage", "trend",
                "min_investment", "hourly_income", "duration_hours"
            ])

        except Exception as e:
            print(f"Stock error {asset.symbol}: {e}")

# ---------- MAIN EXPORTED FUNCTION (Vercel will call this) ----------

def update_all_assets():
    """Single function called by Vercel cron."""
    cryptos = Asset.objects.filter(asset_type="crypto", is_active=True)
    forex   = Asset.objects.filter(asset_type="forex", is_active=True)
    stocks  = Asset.objects.filter(asset_type="stock",  is_active=True)

    update_crypto_prices(cryptos)
    update_forex_prices(forex)
    update_stock_prices(stocks)

    return True
