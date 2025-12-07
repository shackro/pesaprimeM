from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone

from core.models import Currency
from core.utils.currency import convert_amount, get_currency_symbol
import investments
from investments.management.commands.update_asset_prices import update_all_assets
from investments.utils.wallet_stats import calculate_wallet_pnl
from .forms import DepositForm, WithdrawalForm, InvestmentForm
import json
from .models import Asset, EducationalTip, Wallet, Investment, Transaction, Bonus, ContactMessage
from .forms import DepositForm


def get_currency_context(user):
    wallet = user.wallet
    currency_code = user.currency_preference or wallet.currency or "USD"

    current_currency = Currency.objects.filter(code=currency_code, is_active=True).first()
    if not current_currency:
        current_currency = Currency.objects.filter(is_active=True).first()

    currency_code = current_currency.code
    currency_symbol = get_currency_symbol(currency_code)

    return wallet, currency_code, currency_symbol

def update_prices(request):
    """API endpoint to manually trigger asset updates"""
    update_all_assets()
    return JsonResponse({"status": "success", "message": "Prices updated"})

@login_required
def pnl_api(request):
    user = request.user
    wallet = user.wallet

    investments = Investment.objects.filter(user=user, status='active')

    total_invested = investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or 0

    total_current_value = sum(
        inv.units * (inv.asset.current_price or 0)
        for inv in investments
    )

    pnl = total_current_value - total_invested

    currency_code = user.currency_preference or wallet.currency or "KES"

    return JsonResponse({
        "total_invested": float(convert_amount(total_invested, currency_code)),
        "current_value": float(convert_amount(total_current_value, currency_code)),
        "pnl": float(convert_amount(pnl, currency_code)),
    })
    
@login_required
def investment_stats_api(request):
    user = request.user

    # Currency
    current_currency = Currency.objects.filter(
        code=user.currency_preference or "KES",
        is_active=True
    ).first() or Currency.objects.filter(is_active=True).first()

    currency_code = current_currency.code

    stats = calculate_wallet_pnl(user, currency_code, convert_amount)

    progress_width = min(abs(stats["net_pl_percentage"]), 100)

    return JsonResponse({
        "total_profit": stats["total_profit"],
        "total_loss": stats["total_loss"],
        "net_pl": stats["net_pl"],
        "net_pl_percentage": round(stats["net_pl_percentage"], 2),
        "progress_width": progress_width,
        "active_investments": stats["active_investments"],
    })

    

@login_required
def wallet_view(request):
    user = request.user
    now = timezone.now()

    # -------------------
    # WALLET
    # -------------------
    wallet, _ = Wallet.objects.get_or_create(
        user=user,
        defaults={'balance': 0, 'currency': 'USD'}
    )

    # -------------------
    # USER INVESTMENTS
    # -------------------
    investments = Investment.objects.filter(user=user, status='active')

    total_invested = investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or 0

    total_current_value = sum(
        inv.units * (inv.asset.current_price or 0)
        for inv in investments
    )

    total_profit_loss = total_current_value - total_invested

    # -------------------
    # TRANSACTIONS
    # -------------------
    deposits = Transaction.objects.filter(
        user=user, transaction_type='deposit', status='completed'
    )
    withdraws = Transaction.objects.filter(
        user=user, transaction_type='withdraw', status='completed'
    )
    bonuses = Transaction.objects.filter(
        user=user, transaction_type='bonus', status='completed'
    )

    total_deposited = deposits.aggregate(total=Sum('amount'))['total'] or 0
    total_withdrawn = withdraws.aggregate(total=Sum('amount'))['total'] or 0
    total_bonus = bonuses.aggregate(total=Sum('amount'))['total'] or 0

    # -------------------
    # CASH BALANCE & EQUITY
    # -------------------
    wallet.balance = total_deposited + total_bonus - total_withdrawn
    cash_balance = wallet.balance - total_invested
    wallet.equity = cash_balance + total_current_value

    wallet.save(update_fields=["balance", "equity"])

    # -------------------
    # CURRENCY SETTINGS
    # -------------------
    currency_code = user.currency_preference or wallet.currency or "USD"
    current_currency = Currency.objects.filter(code=currency_code, is_active=True).first()
    if not current_currency:
        current_currency = Currency.objects.filter(is_active=True).first()

    currency_code = current_currency.code
    currency_symbol = get_currency_symbol(currency_code)

    # -------------------
    # CONVERT VALUES
    # -------------------
    wallet.balance = convert_amount(wallet.balance, currency_code)
    cash_balance = convert_amount(cash_balance, currency_code)
    wallet.equity = convert_amount(wallet.equity, currency_code)
    total_invested = convert_amount(total_invested, currency_code)
    total_current_value = convert_amount(total_current_value, currency_code)
    total_profit_loss = convert_amount(total_profit_loss, currency_code)

    # -------------------
    # RECENT TRANSACTIONS
    # -------------------
    transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:10]
    for tx in transactions:
        tx.amount = convert_amount(tx.amount, currency_code)

    # -------------------
    # BONUSES
    # -------------------
    available_bonuses = Bonus.objects.filter(user=user, is_claimed=False)
    total_bonuses_earned = Bonus.objects.filter(
        user=user, is_claimed=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    total_bonuses_earned = convert_amount(total_bonuses_earned, currency_code)

    # -------------------
    # STATS
    # -------------------
    deposit_count = deposits.count()
    withdraw_count = withdraws.count()

    monthly_total = deposits.filter(
        created_at__year=now.year,
        created_at__month=now.month
    ).aggregate(total=Sum('amount'))['total'] or 0
    monthly_total = convert_amount(monthly_total, currency_code)

    avg_deposit = (
        deposits.aggregate(total=Sum('amount'))['total'] / deposit_count
        if deposit_count > 0 else 0
    )
    avg_deposit = convert_amount(avg_deposit, currency_code)

    success_rate = (
        deposits.filter(status='completed').count() / deposit_count * 100
        if deposit_count > 0 else 0
    )

    # -------------------
    # CONTEXT
    # -------------------
    context = {
        'wallet': wallet,
        'cash_balance': cash_balance,
        'wallet_equity': wallet.equity,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_profit_loss': total_profit_loss,
        'transactions': transactions,
        'available_bonuses': available_bonuses,
        'total_bonuses_earned': total_bonuses_earned,
        'monthly_total': monthly_total,
        'avg_deposit': avg_deposit,
        'success_rate': success_rate,
        'deposit_count': deposit_count,
        'withdraw_count': withdraw_count,
        'currency_symbol': currency_symbol,
        'currency_code': currency_code,
    }

    return render(request, 'investments/wallet.html', context)

@login_required
def deposit_funds(request):
    user = request.user
    wallet, currency_code, currency_symbol = get_currency_context(user)

    
    investments = Investment.objects.filter(user=user, status='active')

    total_invested = investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or 0

    total_current_value = sum(
        inv.units * (inv.asset.current_price or 0)
        for inv in investments
    )
    
    current_currency = Currency.objects.filter(
        code=user.currency_preference or wallet.currency or "USD",
        is_active=True
    ).first() or Currency.objects.filter(is_active=True).first()

    currency_code = current_currency.code
    currency_symbol = get_currency_symbol(currency_code)

    deposits_qs = Transaction.objects.filter(
        user=user, transaction_type='deposit'
    ).order_by('-created_at')[:5]

    converted_deposits = [
        {
            'id': d.id,
            'payment_method': d.payment_method,
            'amount': convert_amount(d.amount, currency_code),
            'status': d.get_status_display(),
            'created_at': d.created_at,
        }
        for d in deposits_qs
    ]

    base_quick_amounts = [100, 500, 1000, 2000, 5000, 10000]
    quick_amounts = [convert_amount(a, currency_code) for a in base_quick_amounts]

    wallet_balance = convert_amount(wallet.balance - total_invested, currency_code)

    if request.method == "POST":
        form = DepositForm(request.POST, currency_code=currency_code, base_min_amount=100)
        if form.is_valid():
            entered_amount = form.cleaned_data['amount']

            amount_in_base = convert_amount(
                entered_amount, currency_code, reverse=True
            )

            payment_method = form.cleaned_data['payment_method']

            Transaction.objects.create(
                user=user,
                transaction_type='deposit',
                amount=amount_in_base,
                description=f"Deposit via {payment_method}",
                status='completed',
                payment_method=payment_method
            )

            messages.success(
                request,
                f"Deposit of {currency_symbol}{entered_amount} successful!"
            )
            return redirect('investments:deposit')
    else:
        form = DepositForm(currency_code=currency_code, base_min_amount=100)

    return render(request, 'investments/deposit.html', {
        'form': form,
        'wallet': wallet,
        'wallet_balance': wallet_balance,
        'deposits': converted_deposits,
        'quick_amounts': quick_amounts,
        'currency_symbol': currency_symbol,
        'currency_code': currency_code,
    })



@login_required
def withdraw_funds(request):
    user = request.user
    wallet, currency_code, currency_symbol = get_currency_context(user)
    
    investments = Investment.objects.filter(user=user, status='active')

    total_invested = investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or 0

    total_current_value = sum(
        inv.units * (inv.asset.current_price or 0)
        for inv in investments
    )

    converted_wallet_balance = convert_amount(wallet.balance - total_invested, currency_code)

    withdrawals_qs = Transaction.objects.filter(
        user=user, transaction_type='withdraw'
    ).order_by('-created_at')[:5]

    converted_withdrawals = [
        {
            'id': w.id,
            'payment_method': w.payment_method,
            'amount': convert_amount(w.amount, currency_code),
            'status': w.get_status_display(),
            'created_at': w.created_at,
        }
        for w in withdrawals_qs
    ]

    if request.method == "POST":
        form = WithdrawalForm(request.POST, currency_code=currency_code, base_min_amount=100)
        if form.is_valid():
            entered_amount = form.cleaned_data['amount']
            amount_in_base = convert_amount(
                entered_amount, currency_code, reverse=True
            )

            if amount_in_base > wallet.balance:
                messages.error(request, "Insufficient wallet balance.")
                return redirect('investments:withdraw')

            Transaction.objects.create(
                user=user,
                transaction_type='withdraw',
                amount=amount_in_base,
                description="Withdrawal request",
                status='pending',
                payment_method=form.cleaned_data['payment_method']
            )

            messages.success(
                request,
                f"Withdrawal request of {currency_symbol}{entered_amount} submitted."
            )
            return redirect('investments:withdraw')
    else:
        form = WithdrawalForm(currency_code=currency_code, base_min_amount=100)

    return render(request, 'investments/withdraw.html', {
        'wallet_balance': converted_wallet_balance,
        'currency_symbol': currency_symbol,
        'withdrawals': converted_withdrawals,
        'form': form,
    })



@login_required
def bonus_list(request):
    user = request.user
    wallet, currency_code, currency_symbol = get_currency_context(user)


    investments = Investment.objects.filter(user=user, status='active')

    total_invested = investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or 0

    total_current_value = sum(
        inv.units * (inv.asset.current_price or 0)
        for inv in investments
    )
    invest = convert_amount(total_invested,currency_code)


    available_bonuses = user.bonuses.filter(is_claimed=False)

    total_bonuses = user.bonuses.filter(is_claimed=True).aggregate(
        total=Sum('amount')
    )['total'] or 0

    converted_available = []
    for b in available_bonuses:
        converted_available.append({
            'id': b.id,
            'title': b.title,
            'amount': convert_amount(b.amount, currency_code),
        })

    converted_total = convert_amount(total_bonuses, currency_code)
    converted_wallet_balance = convert_amount(wallet.balance, currency_code)
    wallet_balance= converted_wallet_balance - invest

    if request.method == 'POST':
        bonus_id = request.POST.get('bonus_id')
        bonus = get_object_or_404(Bonus, id=bonus_id, user=user, is_claimed=False)

        wallet.balance += bonus.amount
        wallet.save()

        bonus.is_claimed = True
        bonus.save()

        messages.success(request, f'Bonus "{bonus.title}" claimed!')
        return redirect('investments:bonus_list')

    context = {
        'wallet_balance': wallet_balance,
        'currency_symbol': currency_symbol,
        'available_bonuses': converted_available,
        'total_bonuses_earned': converted_total,
    }
    return render(request, 'investments/bonus.html', context)


@login_required
def claim_bonus(request, bonus_id):
    """
    Claim a bonus if eligible.
    """
    try:
        bonus = Bonus.objects.get(id=bonus_id, user=request.user)
    except Bonus.DoesNotExist:
        messages.error(request, "Bonus not found.")
        return redirect('investments:wallet')

    if bonus.claim():
        messages.success(request, f"Bonus '{bonus.title}' claimed successfully!")
    else:
        messages.error(request, f"Bonus '{bonus.title}' cannot be claimed.")

    return redirect('investments:wallet')


ALLOWED_HOURS = [3,4,6,8,10,12,16,18,22]

@login_required
def assets_view(request):
    user = request.user

    # -------------------
    # WALLET
    # -------------------
    wallet, _ = Wallet.objects.get_or_create(user=user)

    # -------------------
    # USER INVESTMENTS
    # -------------------
    investments = Investment.objects.filter(user=user, status='active')

    total_invested = investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or 0

    total_current_value = sum(
        inv.units * (inv.asset.current_price or 0)
        for inv in investments
    )

    total_profit_loss = total_current_value - total_invested

    # -------------------
    # TRANSACTIONS
    # -------------------
    deposits = Transaction.objects.filter(
        user=user, transaction_type='deposit', status='completed'
    )
    withdrawals = Transaction.objects.filter(
        user=user, transaction_type='withdraw', status='completed'
    )
    bonuses = Transaction.objects.filter(
        user=user, transaction_type='bonus', status='completed'
    )

    total_deposited = deposits.aggregate(total=Sum('amount'))['total'] or 0
    total_withdrawn = withdrawals.aggregate(total=Sum('amount'))['total'] or 0
    total_bonus = bonuses.aggregate(total=Sum('amount'))['total'] or 0

    # -------------------
    # WALLET ACCOUNTING (FINAL)
    # -------------------
    wallet.balance = total_deposited + total_bonus - total_withdrawn
    cash_balance = wallet.balance - total_invested
    wallet.equity = cash_balance + total_current_value

    wallet.save(update_fields=["balance", "equity"])

    # -------------------
    # CURRENCY SETTINGS
    # -------------------
    current_currency = Currency.objects.filter(
        code=user.currency_preference or wallet.currency or "KES",
        is_active=True
    ).first() or Currency.objects.filter(is_active=True).first()

    currency_code = current_currency.code
    currency_symbol = get_currency_symbol(currency_code)

    # -------------------
    # CONVERSIONS
    # -------------------
    wallet.balance = convert_amount(wallet.balance, currency_code)
    cash_balance = convert_amount(cash_balance, currency_code)
    wallet.equity = convert_amount(wallet.equity, currency_code)

    total_invested = convert_amount(total_invested, currency_code)
    total_current_value = convert_amount(total_current_value, currency_code)
    total_profit_loss = convert_amount(total_profit_loss, currency_code)

    # -------------------
    # CONVERT INVESTMENTS
    # -------------------
    converted_investments = []
    for inv in investments:
        inv.entry_price = convert_amount(inv.entry_price or 0, currency_code)
        inv.current_value = convert_amount(
            inv.units * (inv.asset.current_price or 0),
            currency_code
        )
        inv.profit_loss = convert_amount(
            inv.current_value - inv.invested_amount,
            currency_code
        )
        converted_investments.append(inv)

    # -------------------
    # MARKET ASSETS
    # -------------------
    market_assets = Asset.objects.filter(is_active=True)

    sorted_assets = sorted(
        market_assets,
        key=lambda x: getattr(x, 'change_percentage', 0) or 0,
        reverse=True
    )

    top_gainers = sorted_assets[:5]
    top_losers = sorted_assets[-5:][::-1] if len(sorted_assets) >= 5 else []

    for asset in market_assets:
        asset.display_price = convert_amount(asset.current_price or 0, currency_code)
        asset.display_hourly_income = convert_amount(asset.hourly_income or 0, currency_code)
        asset.display_min_investment = convert_amount(asset.min_investment or 0, currency_code)

    # -------------------
    # EDUCATIONAL TIPS
    # -------------------
    educational_tips = EducationalTip.objects.filter(
        is_active=True
    ).order_by('-created_at')[:5]

    # -------------------
    # CONTEXT
    # -------------------
    context = {
        'wallet': wallet,
        'wallet_balance': cash_balance,
        'wallet_equity': wallet.equity,
        'investments': converted_investments,
        'user_investments': converted_investments,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_profit_loss': total_profit_loss,
        'market_assets': market_assets,
        'top_gainers': top_gainers,
        'top_losers': top_losers,
        'educational_tips': educational_tips,
        'currency_code': currency_code,
        'currency_symbol': currency_symbol,
        'current_currency': current_currency,
        'allowed_hours': ALLOWED_HOURS,
    }

    return render(request, 'investments/assets.html', context)


@login_required
def investments_page(request):
    user = request.user
    wallet = getattr(user, 'wallet', None)
    if wallet is None:
        wallet = Wallet.objects.create(user=user, balance=Decimal('0.00'), currency='KES')

    currency_code = getattr(user, 'currency_preference', wallet.currency or 'KES')
    currency_symbol = get_currency_symbol(currency_code)

    assets = Asset.objects.filter(is_active=True)

    # Convert display values
    for asset in assets:
        asset.display_price = convert_amount(asset.current_price, currency_code)
        asset.display_hourly_income = convert_amount(asset.hourly_income, currency_code)
        asset.display_min_investment = convert_amount(asset.min_investment, currency_code)

    # Top 5 gainers and losers
    top_gainers = sorted(assets, key=lambda x: x.change_percentage, reverse=True)[:5]
    top_losers = sorted(assets, key=lambda x: x.change_percentage)[:5]

    # User investments
    user_investments = Investment.objects.filter(user=user, status='open')
    for inv in user_investments:
        inv.display_invested_amount = convert_amount(inv.invested_amount, currency_code)
        inv.display_current_value = convert_amount(inv.current_value, currency_code)
        inv.display_profit_loss = convert_amount(inv.profit_loss, currency_code)

    wallet_display_balance = convert_amount(wallet.balance, currency_code)
    wallet_display_equity = convert_amount(wallet.equity, currency_code)

    tips = EducationalTip.objects.filter(is_active=True).order_by('-created_at')[:6]

    default_min = Decimal('350.00')
    investment_form = InvestmentForm(currency_code=currency_code, min_investment_base=default_min)
    quick_amounts_display = [100, 500, 1000, 5000]
    quick_amounts_base = [convert_amount(a, currency_code, reverse=True) for a in quick_amounts_display]
    quick_amounts = list(zip(quick_amounts_display, quick_amounts_base))

    context = {
        'assets': assets,
        'user_investments': user_investments,
        'wallet_balance': wallet_display_balance,
        'wallet_equity': wallet_display_equity,
        'currency_code': currency_code,
        'currency_symbol': currency_symbol,
        'investment_form': investment_form,
        'educational_tips': tips,
        'min_investment_display': convert_amount(default_min, currency_code),
        'quick_amounts': quick_amounts,
        'top_gainers': top_gainers,
        'top_losers': top_losers,
    }
    return render(request, 'investments/investments.html', context)


@login_required
def invest_view(request, asset_id):
    """
    Handles an investment placement for a given asset.
    The user posts an amount in DISPLAY currency. We convert to base (KES) before saving.
    Wallet equity is calculated as: balance + total profit/loss from active investments.
    """
    user = request.user
    wallet = getattr(user, 'wallet', None)
    asset = get_object_or_404(Asset, id=asset_id, is_active=True)

    if wallet is None:
        messages.error(request, "Wallet missing. Contact support.")
        return redirect('investments:investments')

    currency_code = getattr(user, 'currency_preference', wallet.currency or 'KES')
    currency_symbol = get_currency_symbol(currency_code)

    base_min = asset.min_investment

    if request.method == 'POST':
        form = InvestmentForm(request.POST, currency_code=currency_code, min_investment_base=base_min)
        if form.is_valid():
            entered_amount_display = Decimal(form.cleaned_data['amount'])
            duration_hours = int(form.cleaned_data['duration_hours'])

            # Convert to base currency (KES)
            try:
                amount_in_base = convert_amount(entered_amount_display, currency_code, reverse=True)
            except TypeError:
                messages.error(
                    request, 
                    "Currency conversion function incompatible. Update convert_amount to accept reverse=True."
                )
                return redirect('investments:investments')

            if amount_in_base > wallet.balance:
                messages.error(request, "Insufficient wallet balance.")
                return redirect('investments:investments')

            entry_price = asset.current_price
            if entry_price <= 0:
                messages.error(request, "Asset price invalid or unavailable.")
                return redirect('investments:assets')

            # Calculate units
            units = (Decimal(amount_in_base) / Decimal(entry_price)).quantize(Decimal('0.00000001'))

            # Create investment
            inv = Investment.objects.create(
                user=user,
                asset=asset,
                invested_amount=amount_in_base,
                entry_price=entry_price,
                units=units,
                duration_hours=duration_hours,
                start_time=timezone.now(),
            )

            # Log transaction
            Transaction.objects.create(
                user=user,
                transaction_type='investment',
                amount=amount_in_base,
                description=f"Invested in {asset.name}",
                status='completed'
            )

            # Reduce wallet balance but don't count invested amount as lost — equity includes active investments
            wallet.balance -= amount_in_base
            wallet.total_invested += amount_in_base

            # Recalculate equity: balance + sum of profit/loss on active investments
            active_investments = Investment.objects.filter(user=user, status='active')
            total_profit_loss = sum([
                (inv.units * inv.asset.current_price - inv.invested_amount) for inv in active_investments
            ])
            wallet.equity = wallet.balance + total_profit_loss
            wallet.save(update_fields=['balance', 'total_invested', 'equity'])

            messages.success(
                request,
                f"Investment placed: {currency_symbol}{entered_amount_display} ({amount_in_base} KES) into {asset.name}"
            )
            return redirect('investments:assets')
        else:
            messages.error(
                request,
                "Invalid input: " + "; ".join(sum([list(v) for v in form.errors.values()], []))
            )
            return redirect('investments:assets')
    else:
        form = InvestmentForm(
            currency_code=currency_code,
            min_investment_base=base_min,
            initial={'duration_hours': getattr(asset, 'duration_hours_default', 3)}
        )
        context = {
            'asset': asset,
            'form': form,
            'currency_code': currency_code,
            'currency_symbol': currency_symbol,
            'min_investment_display': convert_amount(base_min, currency_code),
        }
        return render(request, 'investments/invest_asset.html', context)



# Helper that can be called from a scheduled job (cron/management command) to auto-close due investments.
def auto_close_due_investments():
    due = Investment.objects.filter(status='open', end_time__lte=timezone.now())
    for inv in due:
        # refresh live price from asset (or market feed)
        inv.recalc_current(inv.asset.current_price)
        inv.close(by_admin=False)