import datetime
from pyexpat.errors import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q
from core.utils.currency import convert_amount, get_currency_symbol
from .models import ContactMessage, Currency
from investments.models import Wallet, Investment, Asset, Transaction
from investments.forms import ContactForm
from django.http import JsonResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta, timezone
from investments.forms import DepositForm 


def switch_currency(request):
    if request.method == "POST":
        code = request.POST.get("currency")

        currency = Currency.objects.filter(code=code, is_active=True).first()
        if currency:
            if request.user.is_authenticated:
                request.user.currency_preference = currency.code
                request.user.save()
            else:
                response = redirect(request.META.get("HTTP_REFERER", "/"))
                response.set_cookie("currency", currency.code)
                return response

    return redirect(request.META.get("HTTP_REFERER", "/"))

ALLOWED_HOURS = [3,4,6,8,10,12,16,18,22]

@login_required
def home_view(request):
    user = request.user
    wallet, created = Wallet.objects.get_or_create(user=user)
    investments = Investment.objects.filter(user=user, status='active')

    total_invested = investments.aggregate(total=Sum('invested_amount'))['total'] or 0
        # Compute total_current_value dynamically
    total_current_value = sum(inv.units * inv.asset.current_price for inv in investments)
    total_profit_loss = total_current_value - total_invested


    total_deposited = Transaction.objects.filter(user=user, transaction_type='deposit', status='completed').aggregate(total=Sum('amount'))['total'] or 0
    total_withdrawn = Transaction.objects.filter(user=user, transaction_type='withdrawal', status='completed').aggregate(total=Sum('amount'))['total'] or 0
    total_bonus = Transaction.objects.filter(user=user, transaction_type='bonus', status='completed').aggregate(total=Sum('amount'))['total'] or 0

    wallet.balance = total_deposited + total_bonus - total_withdrawn
    wallet.equity = total_current_value
    wallet.save()

    recent_activities = Transaction.objects.filter(user=user).order_by('-created_at')[:5]
    market_assets = Asset.objects.filter(is_active=True).order_by('?')[:12]

    # Get user currency
    current_currency = None
    if request.user.is_authenticated:
        code = request.user.currency_preference or 'KES'
        current_currency = Currency.objects.filter(code=code, is_active=True).first()
    if not current_currency:
        current_currency = Currency.objects.filter(is_active=True).first()
    
    currency_code = current_currency.code
    currency_symbol = get_currency_symbol(currency_code)

    # Convert amounts
    wallet.balance = convert_amount(wallet.balance, currency_code)
    wallet.equity = convert_amount(wallet.equity, currency_code)
    total_invested = convert_amount(total_invested, currency_code)
    total_current_value = convert_amount(total_current_value, currency_code)
    total_profit_loss = convert_amount(total_profit_loss, currency_code)
    total_deposited = convert_amount(total_deposited, currency_code)
    total_withdrawn = convert_amount(total_withdrawn, currency_code)
    total_bonus = convert_amount(total_bonus, currency_code)

    for inv in investments:
        inv.entry_price = convert_amount(inv.entry_price, currency_code)
        inv.current_value = convert_amount(inv.units * inv.asset.current_price, currency_code)
        inv.profit_loss = convert_amount(inv.current_value - inv.invested_amount, currency_code)


    for act in recent_activities:
        act.amount = convert_amount(act.amount, currency_code)

    for asset in market_assets:
        asset.display_price = convert_amount(asset.current_price or 0, currency_code)
        asset.display_hourly_income = convert_amount(asset.hourly_income or 0, currency_code)
        asset.display_min_investment = convert_amount(asset.min_investment or 0, currency_code)


    context = {
        'wallet': wallet,
        'allowed_hours': ALLOWED_HOURS,
        'investments': investments,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_profit_loss': total_profit_loss,
        'recent_activities': recent_activities,
        'market_assets': market_assets,
        'total_deposited': total_deposited,
        'total_withdrawn': total_withdrawn,
        'total_bonus': total_bonus,
        'current_currency': current_currency,
        'currency_symbol': currency_symbol,
    }

    return render(request, 'core/home.html', context)


@login_required
def transaction_history_view(request):
    """Full transaction history"""
    # Similar to wallet_view but with all transactions
    context = {
        'page_title': 'Transaction History',
    }
    return render(request, 'core/transaction_history.html', context)

def about_view(request):
    return render(request, 'core/about.html')

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('core:contact_success')
    else:
        form = ContactForm()
    
    return render(request, 'core/contact.html', {'form': form})

def contact_success_view(request):
    return render(request, 'core/contact_success.html')

def terms_view(request):
    return render(request, 'core/terms.html')

def privacy_view(request):
    return render(request, 'core/privacy.html')

def faq_view(request):
    return render(request, 'core/faq.html')


def newsletter_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # In production, save to database or send to email service
            messages.success(request, 'Thank you for subscribing to our newsletter!')
        else:
            messages.error(request, 'Please provide a valid email address.')
    return redirect(request.META.get('HTTP_REFERER', 'core:home'))

def number_carousel_view(request):
    # Generate random numbers for the carousel
    import random
    numbers = []
    for _ in range(20):
        numbers.append({
            'phone': f"+254 7{random.randint(10, 99)} xxx {random.randint(10, 99)}",
            'profit': random.choice([25, 22, -3, -43, 50, 75, -15, -30, 10, 35, -5, 60, -2, -28, 2, 90, -45, 20, -10, 45, 5, -20, 30]),
            'amount': random.randint(5000, 100000)
        })
    return JsonResponse({'numbers': numbers})