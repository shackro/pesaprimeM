from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone

from core.models import Currency
from core.utils.currency import convert_amount, get_currency_symbol
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


@login_required
def wallet_view(request):
    user = request.user
    now = timezone.now()

    # -------------------
    # WALLET
    # -------------------
    wallet, created = Wallet.objects.get_or_create(
        user=user,
        defaults={'balance': 0.00, 'currency': 'USD'}
    )

    # -------------------
    # CURRENCY SETTINGS
    # -------------------
    # Determine user's preferred currency or fallback
    currency_code = user.currency_preference or wallet.currency or "USD"
    current_currency = Currency.objects.filter(code=currency_code, is_active=True).first()
    if not current_currency:
        current_currency = Currency.objects.filter(is_active=True).first()
    currency_code = current_currency.code
    currency_symbol = get_currency_symbol(currency_code)

    # -------------------
    # RECENT TRANSACTIONS
    # -------------------
    transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:10]

    # Convert transaction amounts
    for tx in transactions:
        tx.amount = convert_amount(tx.amount, currency_code)

    # -------------------
    # BONUSES
    # -------------------
    available_bonuses = Bonus.objects.filter(user=user, is_claimed=False)
    total_bonuses_earned = Bonus.objects.filter(user=user, is_claimed=True).aggregate(
        total=Sum('amount')
    )['total'] or 0
    total_bonuses_earned = convert_amount(total_bonuses_earned, currency_code)

    # -------------------
    # TRANSACTION COUNTS
    # -------------------
    deposits = Transaction.objects.filter(user=user, transaction_type='deposit')
    withdraws = Transaction.objects.filter(user=user, transaction_type='withdraw')

    deposit_count = deposits.count()
    withdraw_count = withdraws.count()

    # -------------------
    # MONTHLY TOTAL
    # -------------------
    monthly_total = deposits.filter(
        created_at__year=now.year,
        created_at__month=now.month
    ).aggregate(total=Sum('amount'))['total'] or 0
    monthly_total = convert_amount(monthly_total, currency_code)

    # -------------------
    # AVG DEPOSIT
    # -------------------
    avg_deposit = (deposits.aggregate(total=Sum('amount'))['total'] / deposit_count) if deposit_count > 0 else 0
    avg_deposit = convert_amount(avg_deposit, currency_code)

    # -------------------
    # SUCCESS RATE
    # -------------------
    successful_deposits = deposits.filter(status='completed').count()
    success_rate = (successful_deposits / deposit_count * 100) if deposit_count > 0 else 0

    # -------------------
    # CONVERT WALLET BALANCE
    # -------------------
    wallet.balance = convert_amount(wallet.balance, currency_code)
    wallet.equity = convert_amount(wallet.equity, currency_code)

    # -------------------
    # CONTEXT
    # -------------------
    context = {
        'wallet': wallet,
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
    # RECENT DEPOSITS
    # -------------------
    deposits_qs = Transaction.objects.filter(
        user=user, transaction_type='deposit'
    ).order_by('-created_at')[:5]

    converted_deposits = []
    for deposit in deposits_qs:
        converted_amount = convert_amount(deposit.amount, currency_code)
        converted_deposits.append({
            'id': deposit.id,
            'payment_method': deposit.payment_method,
            'amount': converted_amount,
            'status': deposit.get_status_display(),
            'created_at': deposit.created_at,
        })

    # -------------------
    # QUICK SELECT AMOUNTS
    # -------------------
    base_quick_amounts = [100, 500, 1000, 2000, 5000, 10000]  # default currency (e.g., KES)
    quick_amounts = [convert_amount(amount, currency_code) for amount in base_quick_amounts]

    # -------------------
    # CONVERT WALLET BALANCE
    # -------------------
    wallet.balance = convert_amount(wallet.balance, currency_code)
    wallet_balance = convert_amount(wallet.balance, currency_code)

    # -------------------
    # HANDLE DEPOSIT FORM
    # -------------------
    if request.method == "POST":
        form = DepositForm(
            request.POST,
            currency_code=currency_code,      # pass current user currency
            base_min_amount=100                # your base min in KES
        )
        if form.is_valid():
            # User entered amount in selected currency
            entered_amount = form.cleaned_data['amount']

            # Convert back to wallet/base currency before saving
            amount_in_base_currency = convert_amount(
                entered_amount, currency_code, reverse=True
            )

            payment_method = form.cleaned_data['payment_method']

            Transaction.objects.create(
                user=user,
                transaction_type='deposit',
                amount=amount_in_base_currency,  # saved in base currency
                description=f"Deposit via {payment_method}",
                status='completed',
                payment_method=payment_method,
                created_at=timezone.now()
            )

            # Update wallet balance in base currency
            wallet.balance += amount_in_base_currency
            wallet.save()

            messages.success(
                request, 
                f"Deposit of {currency_symbol}{entered_amount} successful!"
            )
            return redirect('investments:deposit')
    else:
        form = DepositForm(
            request.POST or None,
            currency_code=currency_code,
            base_min_amount=100  # your minimum base amount
        )

    context = {
        'form': form,
        'wallet': wallet,
        'wallet_balance': wallet_balance,
        'deposits': converted_deposits,
        'quick_amounts': quick_amounts,
        'currency_symbol': currency_symbol,
        'currency_code': currency_code,
    }
    return render(request, 'investments/deposit.html', context)


@login_required
def withdraw_funds(request):
    user = request.user
    wallet, currency_code, currency_symbol = get_currency_context(user)

    converted_wallet_balance = convert_amount(wallet.balance, currency_code)

    withdrawals_qs = Transaction.objects.filter(
        user=user, transaction_type='withdraw'
    ).order_by('-created_at')[:5]

    converted_withdrawals = []
    for w in withdrawals_qs:
        converted_withdrawals.append({
            'id': w.id,
            'payment_method': w.payment_method,
            'amount': convert_amount(w.amount, currency_code),
            'status': w.get_status_display(),
            'created_at': w.created_at,
        })

    if request.method == "POST":
        form = WithdrawalForm(
            request.POST,
            currency_code=currency_code,      # current user-selected currency # wallet base currency
            base_min_amount=100                # minimum in KES
        )
        if form.is_valid():
            # User entered amount in selected currency
            entered_amount = form.cleaned_data['amount']

            # Convert back to wallet/base currency before saving
            amount_in_base_currency = convert_amount(
                entered_amount, currency_code, reverse=True
            )

            payment_method = form.cleaned_data['payment_method']

            # Check if user has enough balance in base currency
            if amount_in_base_currency > wallet.balance:
                messages.error(request, "Insufficient wallet balance.")
                return redirect('investments:withdraw')

            # Create withdrawal transaction
            Transaction.objects.create(
                user=user,
                transaction_type='withdraw',
                amount=amount_in_base_currency,  # saved in base currency
                description=f"Withdrawal via {payment_method}",
                status='pending',  # typically pending for withdrawals
                payment_method=payment_method,
                created_at=timezone.now()
            )

            # Deduct from wallet balance (base currency)
            wallet.balance -= amount_in_base_currency
            wallet.save()

            messages.success(
                request,
                f"Withdrawal request of {currency_symbol}{entered_amount} submitted."
            )
            return redirect('investments:withdraw')
    else:
        form = WithdrawalForm(
            request.POST or None,
            currency_code=currency_code,
            base_min_amount=100
        )


    context = {
        'wallet_balance': converted_wallet_balance,
        'currency_symbol': currency_symbol,
        'withdrawals': converted_withdrawals,
        'form': form,
    }
    return render(request, 'investments/withdraw.html', context)



@login_required
def bonus_list(request):
    user = request.user
    wallet, currency_code, currency_symbol = get_currency_context(user)

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
        'wallet_balance': converted_wallet_balance,
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

    # Ensure wallet exists
    wallet, _ = Wallet.objects.get_or_create(
        user=user,
        defaults={'balance': 0.00, 'currency': 'KES'}
    )

    # -------------------
    # CURRENCY SETTINGS
    # -------------------
    currency_code = user.currency_preference or wallet.currency or "KES"
    current_currency = Currency.objects.filter(code=currency_code, is_active=True).first()
    if not current_currency:
        current_currency = Currency.objects.filter(is_active=True).first()
    currency_code = current_currency.code
    currency_symbol = get_currency_symbol(currency_code)

    # -------------------
    # WALLET SUMMARY
    # -------------------
    wallet_balance = convert_amount(wallet.balance, currency_code)
    wallet_equity = convert_amount(getattr(wallet, 'equity', 0) or 0, currency_code)

    # -------------------
    # USER INVESTMENTS
    # -------------------
    user_investments_qs = Investment.objects.filter(user=user, status='active')
    converted_user_investments = []
    total_invested = 0
    total_profit_loss = 0

    for inv in user_investments_qs:
        asset = inv.asset
        current_price = asset.current_price or 0
        invested = convert_amount(inv.invested_amount or 0, currency_code)
        current_value = convert_amount(inv.units * current_price, currency_code)
        profit_loss = convert_amount(current_value - invested, currency_code)

        total_invested += invested
        total_profit_loss += profit_loss

        converted_user_investments.append({
            'id': inv.id,
            'asset': asset,
            'units': inv.units,
            'entry_price': convert_amount(inv.entry_price or 0, currency_code),
            'current_price': convert_amount(current_price, currency_code),
            'current_value': current_value,
            'profit_loss': profit_loss,
            'profit_loss_percentage': getattr(inv, 'profit_loss_percentage', 0),
            'invested_amount': invested,
        })

    # -------------------
    # MARKET ASSETS (set display fields for template)
    # -------------------
    market_assets = list(Asset.objects.filter(is_active=True))
    for asset in market_assets:
        asset.display_price = convert_amount(asset.current_price or 0, currency_code)
        asset.display_hourly_income = convert_amount(asset.hourly_income or 0, currency_code)
        asset.display_min_investment = convert_amount(asset.min_investment or 0, currency_code)

    # -------------------
    # TOP GAINERS / LOSERS
    # -------------------
    sorted_assets = sorted(market_assets, key=lambda x: getattr(x, 'change_percentage', 0) or 0, reverse=True)
    top_gainers = sorted_assets[:5]
    top_losers = sorted_assets[-5:][::-1] if len(sorted_assets) >= 5 else sorted_assets[::-1]

    # -------------------
    # EDUCATIONAL TIPS
    # -------------------
    educational_tips = EducationalTip.objects.filter(is_active=True).order_by('-created_at')[:5]

    # -------------------
    # CONTEXT -> pass both raw and converted values
    # -------------------
    context = {
        # wallet
        'wallet_balance': wallet_balance,
        'wallet_equity': wallet_equity,
        
        'allowed_hours': ALLOWED_HOURS,

        # user investments
        'user_investments': converted_user_investments,
        'investments': converted_user_investments,  # templates expect both keys

        # totals
        'total_invested': total_invested,
        'total_profit_loss': total_profit_loss,

        # market assets (with display_* set)
        'market_assets': market_assets,
        'top_gainers': top_gainers,
        'top_losers': top_losers,

        # educational tips
        'educational_tips': educational_tips,

        # currency
        'currency_code': currency_code,
        'currency_symbol': currency_symbol,
        'current_currency': current_currency,

        # include raw wallet object
        'wallet': wallet,
    }

    return render(request, 'investments/assets.html', context)



# @login_required
# def investments_page(request):
#     """
#     Show the main investments page containing asset list, user's active investments,
#     wallet summary and an investment form for selected asset (investment.html).
#     """
#     user = request.user
#     wallet = getattr(user, 'wallet', None)
#     if wallet is None:
#         # create wallet if missing (keeps app robust)
#         wallet = Wallet.objects.create(user=user, balance=Decimal('0.00'), currency='KES')

#     # currency selection
#     currency_code = getattr(user, 'currency_preference', wallet.currency or 'KES')
#     currency_symbol = get_currency_symbol(currency_code)

#     # Fetch assets (active)
#     assets = Asset.objects.filter(is_active=True).order_by('-change_percentage')

#     # Convert asset display values for template
#     for asset in assets:
#         asset.display_price = convert_amount(asset.current_price, currency_code)
#         asset.display_hourly_income = convert_amount(asset.hourly_income, currency_code)
#         asset.display_min_investment = convert_amount(asset.min_investment, currency_code)

#     # User investments
#     user_investments = Investment.objects.filter(user=user, status='open')
#     # convert matching values for display
#     for inv in user_investments:
#         inv.display_invested_amount = convert_amount(inv.invested_amount, currency_code)
#         inv.display_current_value = convert_amount(inv.current_value, currency_code)
#         inv.display_profit_loss = convert_amount(inv.profit_loss, currency_code)

#     # Wallet display
#     wallet_display_balance = convert_amount(wallet.balance, currency_code)
#     wallet_display_equity = convert_amount(wallet.equity, currency_code)

#     # educational tips
#     tips = EducationalTip.objects.filter(is_active=True).order_by('-created_at')[:6]

#     # forms: default form (currency-aware). We'll instantiate per-asset on the template via JS or invest view
#     default_min = Decimal('350.00')
#     investment_form = InvestmentForm(currency_code=currency_code, min_investment_base=default_min)
#     quick_amounts_display = [100, 500, 1000, 5000]  # or however you generate them
#     quick_amounts_base = [convert_amount(a, currency_code, reverse=True) for a in quick_amounts_display]

#     # create zipped list
#     quick_amounts = list(zip(quick_amounts_display, quick_amounts_base))

#     context = {
#         'assets': assets,
#         'user_investments': user_investments,
#         'wallet_balance': wallet_display_balance,
#         'wallet_equity': wallet_display_equity,
#         'currency_code': currency_code,
#         'currency_symbol': currency_symbol,
#         'investment_form': investment_form,
#         'educational_tips': tips,
#         'min_investment_display': convert_amount(default_min, currency_code),
#         'quick_amounts': quick_amounts,
#     }
#     return render(request, 'investments/investments.html', context)

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
    """
    user = request.user
    wallet = getattr(user, 'wallet', None)
    asset = get_object_or_404(Asset, id=asset_id, is_active=True)

    if wallet is None:
        messages.error(request, "Wallet missing. Contact support.")
        return redirect('investments:investments')

    currency_code = getattr(user, 'currency_preference', wallet.currency or 'KES')
    currency_symbol = get_currency_symbol(currency_code)

    # base min (KES) enforced
    base_min = asset.min_investment

    if request.method == 'POST':
        form = InvestmentForm(request.POST, currency_code=currency_code, min_investment_base=base_min)
        if form.is_valid():
            entered_amount_display = Decimal(form.cleaned_data['amount'])
            duration_hours = int(form.cleaned_data['duration_hours'])

            # Convert display -> base KES
            try:
                amount_in_base = convert_amount(entered_amount_display, currency_code, reverse=True)
            except TypeError:
                # fallback if convert_amount signature does not have reverse param:
                # assume convert_amount(base -> display): so we must divide by rate manually.
                # In that case your convert_amount should be updated. For now raise.
                messages.error(request, "Currency conversion function is incompatible. Update core.utils.currency.convert_amount to accept reverse=True.")
                return redirect('investments:investments')

            # Ensure wallet has enough balance (wallet stores base currency)
            if amount_in_base > wallet.balance:
                messages.error(request, "Insufficient balance (base currency). Please deposit.")
                return redirect('investments:investments')

            # create investment units based on entry price (current asset price is in base)
            entry_price = asset.current_price
            if entry_price <= 0:
                messages.error(request, "Asset price invalid or not available.")
                return redirect('investments:assets')

            units = (Decimal(amount_in_base) / Decimal(entry_price)).quantize(Decimal('0.00000001'))
            

            inv = Investment.objects.create(
                user=user,
                asset=asset,
                invested_amount=amount_in_base,
                entry_price=entry_price,
                units=units,
                duration_hours=duration_hours,
                start_time=timezone.now(),
            )

            # create transaction and debit wallet (all in base currency)
            Transaction.objects.create(
                user=user,
                transaction_type='investment',
                amount=amount_in_base,
                description=f"Invested in {asset.name}",
                status='completed'
            )

            wallet.balance -= Decimal(amount_in_base)
            wallet.total_invested += Decimal(amount_in_base)
            wallet.equity += Decimal(amount_in_base)
            wallet.save()

            messages.success(request, f"Investment placed: {currency_symbol}{entered_amount_display} ({amount_in_base} KES) into {asset.name}")
            return redirect('investments:assets')
        else:
            # display errors
            messages.error(request, "Invalid input: " + "; ".join(sum([list(v) for v in form.errors.values()], [])))
            return redirect('investments:assets')
    else:
        # GET: show investing page for asset
        form = InvestmentForm(currency_code=currency_code, min_investment_base=base_min, initial={'duration_hours': asset.duration_hours_default})
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