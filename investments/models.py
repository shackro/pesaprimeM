from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


# ---------------------------------------------------------
# ASSET MODEL (Crypto, Forex, Stocks – 24 total entries)
# ---------------------------------------------------------
class Asset(models.Model):
    ALLOWED_HOURS = [3,4,6,8,10,12,16,18,22]
    
    ASSET_TYPES = [
        ('crypto', 'Cryptocurrency'),
        ('forex', 'Forex/Futures'),
        ('stock', 'Stocks'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)

    # Market Data
    current_price = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    trend = models.CharField(max_length=10, choices=[('up', 'Up'), ('down', 'Down'), ('neutral', 'Neutral')])
    change_percentage = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Chart Data (Simulated + Coingecko Live)
    chart_data = models.JSONField(default=list, blank=True)

    # Investment Rules
    min_investment = models.DecimalField(max_digits=20, decimal_places=2, default=350)  # Base in KES
    hourly_income = models.DecimalField(max_digits=20, decimal_places=2, default=45)  # Base in KES
    duration_hours = models.IntegerField(default=3)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.symbol})"

    @property
    def simulated_return(self):
        """Base earnings in KES before currency conversion."""
        return self.hourly_income


# ---------------------------------------------------------
# USER WALLET
# ---------------------------------------------------------
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    equity = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='KES')
    total_invested = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet"

    def can_withdraw(self, amount):
        return self.balance >= amount


@receiver(post_save, sender=User)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)


# ---------------------------------------------------------
# INVESTMENT MODEL (Main system)
# ---------------------------------------------------------
class Investment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('pending_close', 'Pending Admin Approval'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_investments")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    # Invested Details
    invested_amount = models.DecimalField(max_digits=20, decimal_places=2)
    entry_price = models.DecimalField(max_digits=20, decimal_places=4)
    units = models.DecimalField(max_digits=20, decimal_places=8)

    # Duration & Auto-close
    duration_hours = models.PositiveIntegerField(default=4)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    profit_loss = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def is_duration_complete(self):
        """Investment auto closes once duration is reached."""
        elapsed = timezone.now() - self.start_time
        return elapsed.total_seconds() >= (self.duration_hours * 3600)

    def calculate_profit(self):
        """Based on hourly income (KES base) * hours."""
        hrs = self.duration_hours
        base_income = float(self.asset.hourly_income)
        self.profit_loss = base_income * hrs
        return self.profit_loss

    def close(self, admin=False):
        """Close automatically OR by admin approval."""
        if not admin and not self.is_duration_complete():
            self.status = "pending_close"
            self.save()
            return

        self.status = "closed"
        self.end_time = timezone.now()
        self.calculate_profit()

        # Add profit to wallet
        wallet = self.user.wallet
        wallet.balance += self.profit_loss
        wallet.save()

        self.save()

    def __str__(self):
        return f"{self.user.username} - {self.asset.symbol}"


# ---------------------------------------------------------
# TRANSACTIONS (Deposit, Withdraw, Investment, Profit)
# ---------------------------------------------------------

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('investment', 'Investment'),
        ('bonus', 'Bonus'),
        ('profit', 'Profit'),
        ('investment_completion', 'Investment Completion'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # For deposits/withdrawals
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # For investments
    investment = models.ForeignKey(Investment, on_delete=models.SET_NULL, null=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - {self.amount}"
    
    def complete_transaction(self):
        self.status = 'completed'
        self.save()

class Bonus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bonuses')
    title = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    bonus_type = models.CharField(max_length=20, 
                                  choices=[('fixed', 'Fixed'), ('percentage', 'Percentage')])
    min_deposit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    is_claimed = models.BooleanField(default=False)
    claimed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def claim(self):
        if not self.is_claimed and timezone.now() <= self.expires_at:
            wallet = Wallet.objects.get(user=self.user)
            wallet.balance += self.amount
            wallet.save()
            
            self.is_claimed = True
            self.claimed_at = timezone.now()
            self.save()
            
            # Create transaction record
            Transaction.objects.create(
                user=self.user,
                transaction_type='bonus',
                amount=self.amount,
                description=f"Claimed bonus: {self.title}",
                status='completed'
            )
            
            return True
        return False
    
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.subject} - {self.name}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
      

# ---------------------------------------------------------
# EDUCATIONAL TIPS
# ---------------------------------------------------------
class EducationalTip(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
