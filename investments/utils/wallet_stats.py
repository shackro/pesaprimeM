from django.db.models import Sum

from investments.models import Investment

def calculate_wallet_pnl(user, currency_code, convert_amount):
    investments = Investment.objects.filter(user=user, status="active")

    total_invested = investments.aggregate(
        total=Sum("invested_amount")
    )["total"] or 0

    total_current_value = sum(
        inv.units * (inv.asset.current_price or 0)
        for inv in investments
    )

    total_profit_loss = total_current_value - total_invested

    total_profit = sum(
        max((inv.units * inv.asset.current_price) - inv.invested_amount, 0)
        for inv in investments
    )

    total_loss = sum(
        min((inv.units * inv.asset.current_price) - inv.invested_amount, 0)
        for inv in investments
    )

    # ✅ Currency conversion (CRITICAL)
    return {
        "total_invested": convert_amount(total_invested, currency_code),
        "total_current_value": convert_amount(total_current_value, currency_code),
        "total_profit": convert_amount(total_profit, currency_code),
        "total_loss": convert_amount(abs(total_loss), currency_code),
        "net_pl": convert_amount(total_profit_loss, currency_code),
        "net_pl_percentage": (
            (total_profit_loss / total_invested) * 100
            if total_invested > 0 else 0
        ),
        "active_investments": investments.count(),
    }
