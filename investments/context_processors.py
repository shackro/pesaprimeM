from .models import Wallet

def wallet_context(request):
    if request.user.is_authenticated:
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        return {'global_wallet': wallet}
    return {}
