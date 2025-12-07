from decimal import ROUND_HALF_UP, Decimal
from django import forms
from .models import Transaction, ContactMessage
from core.utils.currency import convert_amount  # make sure reverse conversion works if needed


class DepositForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount', 'payment_method']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        # Only expect currency_code and base_min_amount
        self.currency_code = kwargs.pop('currency_code', 'KES')
        self.base_min_amount = kwargs.pop('base_min_amount', 100)
        super().__init__(*args, **kwargs)

        min_amount_converted = convert_amount(self.base_min_amount, self.currency_code)
        self.fields['amount'].widget = forms.NumberInput(
            attrs={'min': str(min_amount_converted), 'step': 'any'}
        )
        self.fields['amount'].min_value = min_amount_converted
        self.fields['amount'].label = f"Amount ({self.currency_code})"


class WithdrawalForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount', 'payment_method']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.currency_code = kwargs.pop('currency_code', 'KES')
        self.base_min_amount = kwargs.pop('base_min_amount', 100)
        super().__init__(*args, **kwargs)

        min_amount_converted = convert_amount(self.base_min_amount, self.currency_code)
        self.fields['amount'].widget = forms.NumberInput(
            attrs={'min': str(min_amount_converted), 'step': 'any'}
        )
        self.fields['amount'].min_value = min_amount_converted
        self.fields['amount'].label = f"Amount ({self.currency_code})"


ALLOWED_HOURS = [3, 4, 6, 8, 10, 12, 16, 18, 22]


class InvestmentForm(forms.Form):
    """
    Form that accepts amount in the user's selected currency (display currency).
    Amount is entered in display currency (e.g. KES, USD) and later converted to base (KES).
    """

    # amount accepts two decimal places for display currencies
    amount = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        min_value=Decimal('1.00'),
        error_messages={
            "required": "Enter an amount.",
            "min_value": "Amount must be at least %(limit_value)s."
        }
    )

    # duration will be a select so the template can't post arbitrary numbers
    duration_hours = forms.ChoiceField(choices=[(h, f"{h} hours") for h in ALLOWED_HOURS])

    confirm = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        """
        kwargs:
            currency_code: string like 'KES' or 'USD' (used for display conversion)
            min_investment_base: Decimal (base currency KES)
        """
        self.currency_code = kwargs.pop('currency_code', 'KES')
        self.min_investment_base = kwargs.pop('min_investment_base', Decimal('350.00'))
        super().__init__(*args, **kwargs)

        # Convert min_investment_base (KES) -> display currency for the widget
        try:
            min_display = convert_amount(self.min_investment_base, self.currency_code)
            # ensure Decimal and quantize to 2 decimal places for display
            if not isinstance(min_display, Decimal):
                min_display = Decimal(str(min_display))
        except TypeError:
            # if convert_amount signature is different, fallback to base
            min_display = Decimal(self.min_investment_base)

        # quantize to 2 decimal places for display (common currency display)
        min_display = min_display.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # set the widget attributes so browser validation is consistent
        self.fields['amount'].widget = forms.NumberInput(attrs={
            'min': str(min_display),
            'step': '0.01',              # IMPORTANT: match decimal precision
            'class': 'border rounded p-2 w-full text-sm',
            'inputmode': 'decimal',      # mobile decimal keyboard
            'placeholder': str(min_display),
        })

        # make sure server-side min_value is set to same Decimal (not string)
        self.fields['amount'].min_value = min_display

        # duration choices already set; optionally set initial
        default_duration = kwargs.get('initial', {}).get('duration_hours', ALLOWED_HOURS[0])
        self.fields['duration_hours'].initial = str(default_duration)

        self.fields['confirm'].widget = forms.CheckboxInput(attrs={
            'class': 'mr-2 accent-blue-600'
        })

    def clean_amount(self):
        """
        Normalize and validate amount:
        - quantize to 2 decimals (display currency)
        - ensure >= min_display
        """
        raw = self.cleaned_data.get('amount')
        if raw is None:
            raise forms.ValidationError("Enter an amount.")

        # ensure Decimal
        amount = Decimal(raw)

        # quantize to 2 decimal places (display currency)
        amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        min_allowed = self.fields['amount'].min_value
        if isinstance(min_allowed, (str, float)):
            min_allowed = Decimal(str(min_allowed))

        if amount < Decimal(str(min_allowed)):
            raise forms.ValidationError(f"Minimum investment is {min_allowed} {self.currency_code}")

        return amount

    def clean_duration_hours(self):
        # we stored choice values as strings so convert back to int
        value = self.cleaned_data.get('duration_hours')
        try:
            hrs = int(value)
        except (TypeError, ValueError):
            raise forms.ValidationError("Invalid duration selected.")

        if hrs not in ALLOWED_HOURS:
            raise forms.ValidationError(f"Duration must be one of: {', '.join(map(str, ALLOWED_HOURS))}")
        return hrs

    

class QuickInvestForm(forms.Form):
    quick_amount = forms.DecimalField(max_digits=20, decimal_places=2)


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
