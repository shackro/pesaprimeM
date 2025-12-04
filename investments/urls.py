from django.urls import path
from . import views

app_name = 'investments'

urlpatterns = [
    path('wallet/', views.wallet_view, name='wallet'),
    path('deposit/', views.deposit_funds, name='deposit'),
    path('withdraw/', views.withdraw_funds, name='withdraw'),
    path('assets/', views.assets_view, name='assets'),
    path('bonus/', views.bonus_list, name='bonus'),
    path('bonus/claim/<uuid:bonus_id>/', views.claim_bonus, name='claim_bonus'),
    path('invest/', views.investments_page, name='investment'),
    path('invest/<uuid:asset_id>/', views.invest_view, name='invest_asset'),
]

