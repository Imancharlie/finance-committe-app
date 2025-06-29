from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Member, Transaction


class CustomLoginForm(AuthenticationForm):
    """Custom login form with Bootstrap styling"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )


class MemberForm(forms.ModelForm):
    """Form for creating/editing members"""
    class Meta:
        model = Member
        fields = ['name', 'pledge', 'phone', 'email', 'course', 'year']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name'
            }),
            'pledge': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '70000',
                'min': '0',
                'step': '0.01'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
            'course': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Course/Program'
            }),
            'year': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Year of Study'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default pledge if creating new member
        if not self.instance.pk:
            self.fields['pledge'].initial = 70000.00


class QuickMemberForm(forms.ModelForm):
    """Simplified form for quick member addition"""
    class Meta:
        model = Member
        fields = ['name', 'pledge']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name'
            }),
            'pledge': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '70000',
                'min': '0',
                'step': '0.01'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pledge'].initial = 70000.00


class TransactionForm(forms.ModelForm):
    """Form for creating transactions"""
    class Meta:
        model = Transaction
        fields = ['amount', 'date', 'note']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount in TZS',
                'min': '0',
                'step': '1000',
                'required': True
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Payment notes (optional)',
                'maxlength': '500'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date to today
        from datetime import date
        self.fields['date'].initial = date.today()
        
        # Set field labels
        self.fields['amount'].label = 'Payment Amount (TZS)'
        self.fields['date'].label = 'Payment Date'
        self.fields['note'].label = 'Notes (Optional)'
        
        # Make amount required
        self.fields['amount'].required = True
        self.fields['date'].required = True

    def clean_amount(self):
        """Validate payment amount"""
        amount = self.cleaned_data.get('amount')
        
        if amount is None:
            raise forms.ValidationError('Payment amount is required.')
        
        if amount <= 0:
            raise forms.ValidationError('Payment amount must be greater than zero.')
        
        if amount > 10000000:  # 10 million TZS limit
            raise forms.ValidationError('Payment amount cannot exceed 10,000,000 TZS.')
        
        return amount

    def clean_date(self):
        """Validate payment date"""
        date = self.cleaned_data.get('date')
        
        if date is None:
            raise forms.ValidationError('Payment date is required.')
        
        from datetime import date as today_date
        today = today_date.today()
        
        # Allow payments up to 30 days in the future (for advance payments)
        from datetime import timedelta
        future_limit = today + timedelta(days=30)
        
        if date > future_limit:
            raise forms.ValidationError('Payment date cannot be more than 30 days in the future.')
        
        return date

    def clean_note(self):
        """Clean and validate note field"""
        note = self.cleaned_data.get('note', '').strip()
        
        if len(note) > 500:
            raise forms.ValidationError('Note cannot exceed 500 characters.')
        
        return note


class MemberUpdateForm(forms.ModelForm):
    """Form for inline member updates"""
    class Meta:
        model = Member
        fields = ['pledge', 'paid_total']
        widgets = {
            'pledge': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': '0',
                'step': '0.01'
            }),
            'paid_total': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': '0',
                'step': '0.01'
            }),
        }


class ExcelImportForm(forms.Form):
    """Form for importing members from Excel file"""
    excel_file = forms.FileField(
        label='Excel File (.xlsx)',
        help_text='Upload an Excel file with columns: Name, Pledge, Phone, Email, Course, Year',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls'
        })
    )
    
    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        label='Update existing members',
        help_text='If checked, will update existing members with matching names',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    default_pledge = forms.DecimalField(
        required=False,
        initial=70000.00,
        label='Default Pledge (if not specified in Excel)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '0.01'
        })
    )

    def clean_excel_file(self):
        file = self.cleaned_data['excel_file']
        if file:
            # Check file extension
            if not file.name.endswith(('.xlsx', '.xls')):
                raise forms.ValidationError('Please upload a valid Excel file (.xlsx or .xls)')
            
            # Check file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError('File size must be less than 5MB')
        
        return file 