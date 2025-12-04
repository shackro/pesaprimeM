import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Sum
from core.models import Currency
from core.utils.currency import convert_amount, get_currency_symbol
from investments.models import Investment, Wallet
from .models import User, UserProfile
from .forms import (UserRegistrationForm, UserLoginForm, 
                    UserUpdateForm, ProfileUpdateForm, PasswordChangeForm)
from django.http import JsonResponse


def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('core:home')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('core:home')
    else:
        form = UserLoginForm()
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')

@login_required
def profile_view(request):
    user = request.user
    profile = user.profile

    # -------------------
    # Handle POST (update profile)
    # -------------------
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=profile)

    # -------------------
    # Investment Stats
    # -------------------
    wallet, _ = Wallet.objects.get_or_create(user=user)

    investments = Investment.objects.filter(user=user, status='active')
    total_invested = investments.aggregate(total=Sum('invested_amount'))['total'] or 0
    total_current_value = sum(inv.units * inv.asset.current_price for inv in investments)
    total_profit_loss = total_current_value - total_invested

    # -------------------
    # Currency Settings
    # -------------------
    currency_code = user.currency_preference or wallet.currency or 'USD'
    current_currency = Currency.objects.filter(code=currency_code, is_active=True).first()
    if not current_currency:
        current_currency = Currency.objects.filter(is_active=True).first()
    currency_code = current_currency.code
    currency_symbol = get_currency_symbol(currency_code)

    # Convert amounts
    total_invested = convert_amount(total_invested, currency_code)
    total_current_value = convert_amount(total_current_value, currency_code)
    total_profit_loss = convert_amount(total_profit_loss, currency_code)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'wallet': wallet,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_profit_loss': total_profit_loss,
        'currency_symbol': currency_symbol,
    }

    return render(request, 'accounts/profile.html', context)

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password']
            
            if user.check_password(current_password):
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully!')
                return redirect('accounts:profile')
            else:
                form.add_error('current_password', 'Current password is incorrect.')
    else:
        form = PasswordChangeForm()
    
    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def update_theme_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            theme = data.get('theme')
            if theme in ['light', 'dark']:
                request.user.theme_preference = theme
                request.user.save()
                return JsonResponse({'success': True})
        except:
            pass
    return JsonResponse({'success': False}, status=400)

@login_required
def update_currency_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            currency = data.get('currency')
            
            # Validate currency exists
            from core.models import Currency
            if Currency.objects.filter(code=currency, is_active=True).exists():
                request.user.currency_preference = currency
                request.user.save()
                return JsonResponse({'success': True})
        except:
            pass
    return JsonResponse({'success': False}, status=400)