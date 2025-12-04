from .models import Currency
from django.conf import settings

def currency_context(request):
    currencies = Currency.objects.filter(is_active=True)
    current_currency = None
    
    if request.user.is_authenticated:
        user_currency = request.user.currency_preference
        current_currency = Currency.objects.filter(code=user_currency).first()
    
    if not current_currency and currencies.exists():
        current_currency = currencies.first()
    
    return {
        'available_currencies': currencies,
        'current_currency': current_currency,
    }

def theme_context(request):
    theme = 'light'
    if request.user.is_authenticated:
        theme = request.user.theme_preference
    elif 'theme' in request.COOKIES:
        theme = request.COOKIES['theme']
    
    return {'theme': theme}