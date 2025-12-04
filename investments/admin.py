from django.contrib import admin
from .models import Wallet, Asset, Investment, Transaction, EducationalTip

# admin.py
from django.contrib import admin
from .models import Wallet, Investment

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'balance', 'total_invested_display', 'profit_loss_display')

    def total_invested_display(self, obj):
        # Sum all active investments for this wallet user
        investments = Investment.objects.filter(user=obj.user, status='active')
        return sum(inv.invested_amount or 0 for inv in investments)

    total_invested_display.short_description = 'Total Invested'

    def profit_loss_display(self, obj):
        investments = Investment.objects.filter(user=obj.user, status='active')
        return sum(inv.profit_loss or 0 for inv in investments)

    profit_loss_display.short_description = 'Profit/Loss'


class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'asset', 'invested_amount', 'current_value_display', 'profit_loss')

    def current_value_display(self, obj):
        return obj.current_value
    current_value_display.short_description = 'Current Value'



@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'asset_type', 'current_price', 'change_percentage', 'is_active')
    list_filter = ('asset_type', 'is_active')
    search_fields = ('name', 'symbol')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status')
    search_fields = ('user__username',)

@admin.register(EducationalTip)
class EducationalTipAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title',)
