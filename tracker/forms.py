from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from .models import Member, Transaction, Organization, OrganizationTheme, OrganizationUser


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
        fields = ['name', 'pledge', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name',
                'required': True
            }),
            'pledge': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Pledge Amount',
                'min': '0',
                'step': '0.01',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number',
                'required': True
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default pledge if creating new member
        if not self.instance.pk:
            self.fields['pledge'].initial = 70000.00
        
        # Set field labels
        self.fields['name'].label = 'Full Name'
        self.fields['pledge'].label = 'Pledge Amount (TZS)'
        self.fields['phone'].label = 'Phone Number'


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

from django import forms
from decimal import Decimal

class ExcelImportForm(forms.Form):
    """Form for importing members and payments from Excel file"""

    excel_file = forms.FileField(
        label='Excel File (.xlsx)',
        help_text=(
            "Upload an Excel file with columns in the following order: "
            "Name (required), Pledge (optional), Paid (optional), Phone, Email, Course, Year"
        ),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx'  # only .xlsx supported by openpyxl
        })
    )

    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        label='Update existing members',
        help_text='If checked, members with the same name will be updated instead of skipped.',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    default_pledge = forms.DecimalField(
        required=False,
        initial=Decimal('70000.00'),
        label='Default Pledge (used when missing in Excel)',
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '0.01'
        })
    )

    def clean_excel_file(self):
        file = self.cleaned_data.get('excel_file')

        if not file:
            raise forms.ValidationError('No file uploaded.')

        # Validate file extension
        if not file.name.endswith('.xlsx'):
            raise forms.ValidationError('Only .xlsx files are supported (Excel 2007+).')

        # Validate file size (max 5MB)
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('The uploaded file is too large. Max size is 5MB.')

        return file


# ============================================================================
# ORGANIZATION ADMIN FORMS
# ============================================================================

class OrganizationSettingsForm(forms.ModelForm):
    """Form for editing organization settings"""
    class Meta:
        model = Organization
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Organization Name',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Organization Description (optional)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'Organization Name'
        self.fields['description'].label = 'Description'
        self.fields['is_active'].label = 'Active'


class OrganizationThemeForm(forms.ModelForm):
    """Form for editing organization theme and branding"""
    class Meta:
        model = OrganizationTheme
        fields = ['logo', 'favicon', 'primary_color', 'secondary_color', 'success_color', 
                  'warning_color', 'danger_color', 'navbar_title', 'footer_text', 'watermark_text']
        widgets = {
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'favicon': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'primary_color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'secondary_color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'success_color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'warning_color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'danger_color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'navbar_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Custom navbar title (optional)'
            }),
            'footer_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Custom footer text (optional)'
            }),
            'watermark_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Watermark text for reports'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['logo'].label = 'Organization Logo'
        self.fields['favicon'].label = 'Favicon'
        self.fields['primary_color'].label = 'Primary Color'
        self.fields['secondary_color'].label = 'Secondary Color'
        self.fields['success_color'].label = 'Success Color'
        self.fields['warning_color'].label = 'Warning Color'
        self.fields['danger_color'].label = 'Danger Color'
        self.fields['navbar_title'].label = 'Custom Navbar Title'
        self.fields['footer_text'].label = 'Footer Text'
        self.fields['watermark_text'].label = 'Watermark Text'


class OrganizationUserForm(forms.ModelForm):
    """Form for managing organization users"""
    class Meta:
        model = OrganizationUser
        fields = ['role', 'is_active']
        widgets = {
            'role': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].label = 'Role'
        self.fields['is_active'].label = 'Active'


class AddOrganizationUserForm(forms.Form):
    """Form for adding new users to organization - now creates users if they don't exist"""
    username = forms.CharField(
        max_length=150,
        label='Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username',
            'required': True
        })
    )
    
    password = forms.CharField(
        max_length=128,
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
            'required': False
        }),
        required=False,
        help_text='Leave empty to auto-generate a password'
    )
    
    role = forms.ChoiceField(
        choices=OrganizationUser.ROLE_CHOICES,
        label='Role',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError('Username is required.')
        if len(username) < 3:
            raise forms.ValidationError('Username must be at least 3 characters long.')
        return username


class SignUpForm(forms.Form):
    """Form for user registration and organization creation"""
    # User fields
    first_name = forms.CharField(
        max_length=30,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your first name',
            'required': True
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your last name',
            'required': True
        })
    )
    
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
            'required': True
        })
    )
    
    username = forms.CharField(
        max_length=150,
        label='Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username',
            'required': True
        })
    )
    
    password = forms.CharField(
        max_length=128,
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a strong password',
            'required': True
        })
    )
    
    password_confirm = forms.CharField(
        max_length=128,
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'required': True
        })
    )
    
    # Organization fields
    organization_name = forms.CharField(
        max_length=255,
        label='Organization Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your organization name',
            'required': True
        })
    )
    
    organization_description = forms.CharField(
        max_length=500,
        label='Organization Description (Optional)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Brief description of your organization',
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data
