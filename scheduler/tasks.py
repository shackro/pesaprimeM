# scheduler/tasks.py
import requests
from decimal import Decimal
import yfinance as yf
from investments.models import Asset
from datetime import datetime

def update_crypto_prices(assets):
    symbol_to_id = {
        "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
        "SOL": "solana", "XRP": "ripple", "ADA": "cardano",
        "DOT": "polkadot", "DOGE": "dogecoin", "LTC": "litecoin", "AVAX": "avalanche-2",
    }
    ids = [symbol_to_id[a.symbol] for a in assets if a.symbol in symbol_to_id]
    if not ids:
        return
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=usd"
    resp = requests.get(url, timeout=10).json()
    for asset in assets:
        cg_id = symbol_to_id.get(asset.symbol)
        if cg_id in resp:
            new_price = Decimal(resp[cg_id]["usd"])
            asset.change_percentage = ((new_price - asset.current_price)/asset.current_price*100) if asset.current_price>0 else 0
            asset.trend = "up" if asset.change_percentage>0 else "down" if asset.change_percentage<0 else "neutral"
            asset.current_price = new_price
            asset.save()
            print(f"[Crypto] {asset.symbol}: {new_price}, Change: {asset.change_percentage:.2f}%")

def update_forex_prices(assets):
    url = "https://api.exchangerate.host/latest?base=USD"
    resp = requests.get(url, timeout=10).json()
    rates = resp.get("rates", {})
    for asset in assets:
        if "/" in asset.symbol:
            base, quote = asset.symbol[:3], asset.symbol[4:]
            rate = rates.get(quote)
            if not rate:
                continue
            new_price = Decimal(rate)
            asset.change_percentage = ((new_price - asset.current_price)/asset.current_price*100) if asset.current_price>0 else 0
            asset.trend = "up" if asset.change_percentage>0 else "down" if asset.change_percentage<0 else "neutral"
            asset.current_price = new_price
            asset.save()
            print(f"[Forex] {asset.symbol}: {new_price}, Change: {asset.change_percentage:.2f}%")

def update_stock_prices(assets):
    for asset in assets:
        try:
            data = yf.Ticker(asset.symbol).history(period="1d")
            if not data.empty:
                new_price = Decimal(data['Close'].iloc[-1])
                asset.change_percentage = ((new_price - asset.current_price)/asset.current_price*100) if asset.current_price>0 else 0
                asset.trend = "up" if asset.change_percentage>0 else "down" if asset.change_percentage<0 else "neutral"
                asset.current_price = new_price
                asset.save()
                print(f"[Stock] {asset.symbol}: {new_price}, Change: {asset.change_percentage:.2f}%")
        except Exception as e:
            print(f"Error updating {asset.symbol}: {e}")

def update_all_assets():
    print(f"[{datetime.now()}] Running scheduled asset update...")
    cryptos = Asset.objects.filter(asset_type="crypto", is_active=True)
    forex = Asset.objects.filter(asset_type="forex", is_active=True)
    stocks = Asset.objects.filter(asset_type="stock", is_active=True)
    update_crypto_prices(cryptos)
    update_forex_prices(forex)
    update_stock_prices(stocks)
    print(f"[{datetime.now()}] Asset update completed.")
