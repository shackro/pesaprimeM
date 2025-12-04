from decimal import Decimal
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
    In the view we will convert to base (KES) before saving.
    """
    amount = forms.DecimalField(max_digits=20, decimal_places=2, min_value=Decimal('1.00'))
    duration_hours = forms.IntegerField(min_value=1, max_value=168, initial=4)
    confirm = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        # expect currency_code and min_investment_base (KES)
        self.currency_code = kwargs.pop('currency_code', 'KES')
        self.min_investment_base = kwargs.pop('min_investment_base', Decimal('350.00'))  # in KES
        super().__init__(*args, **kwargs)

        # convert min to display currency for widget attributes and validation
        try:
            min_display = convert_amount(self.min_investment_base, self.currency_code)
        except TypeError:
            min_display = self.min_investment_base

        # Add Tailwind classes directly to widgets
        tailwind_input_class = (
            "border rounded p-2 w-full text-sm focus:outline-none "
            "focus:ring-2 focus:ring-blue-500"
        )

        self.fields['amount'].widget = forms.NumberInput(attrs={
            'min': str(min_display),
            'step': '1',
            'class': tailwind_input_class
        })
        self.fields['amount'].min_value = min_display

        self.fields['duration_hours'].widget = forms.NumberInput(attrs={
            'min': '1',
            'max': '168',
            'class': tailwind_input_class
        })

        self.fields['confirm'].widget = forms.CheckboxInput(attrs={
            'class': 'mr-2 accent-blue-600'
        })

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        min_allowed = self.fields['amount'].min_value
        if amount < Decimal(str(min_allowed)):
            raise forms.ValidationError(f"Minimum investment is {min_allowed} {self.currency_code}")
        return amount

    def clean_duration_hours(self):
        hrs = int(self.cleaned_data['duration_hours'])
        if hrs not in ALLOWED_HOURS:
            raise forms.ValidationError(f"Duration must be one of: {', '.join(map(str, ALLOWED_HOURS))}")
        return hrs

    

class QuickInvestForm(forms.Form):
    quick_amount = forms.DecimalField(max_digits=20, decimal_places=2)


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
