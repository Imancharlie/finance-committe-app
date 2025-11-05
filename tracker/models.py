from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver

# ============================================================================
# MULTITENANCY MODELS
# ============================================================================

class Organization(models.Model):
    """
    Represents a tenant organization (e.g., a finance committee, church group, etc.)
    Each organization has isolated data: members, transactions, staff.
    """
    CATEGORY_CHOICES = [
        ('organization', 'Organization'),
        ('religious', 'Religious Contribution'),
        ('wedding_sendoff', 'Wedding & Sendoff'),
        ('ceremonies', 'Ceremonies (Graduation, Birthday, etc.)'),
        ('condolence', 'Condolence'),
        ('collection_other', 'Collection & Other'),
    ]

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default='organization')
    # Subscription & Trial
    trial_started_at = models.DateTimeField(blank=True, null=True)
    subscription_expires_at = models.DateTimeField(blank=True, null=True)
    SUBSCRIPTION_STATUS_CHOICES = [
        ('FREE_TRIAL', 'Free Trial'),
        ('NOT_SUBSCRIBED', 'Not Subscribed'),
        ('SUBSCRIBED', 'Subscribed'),
    ]
    subscription_status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default='FREE_TRIAL')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# Default theme colors per category
CATEGORY_DEFAULT_COLORS = {
    'organization': {
        'primary': '#0d6efd',  # Bootstrap blue
        'secondary': '#64748b',
    },
    'religious': {
        'primary': '#7492b9',
        'secondary': '#64748b',
    },
    'wedding_sendoff': {
        'primary': '#ffa8B6',
        'secondary': '#64748b',
    },
    'ceremonies': {
        'primary': '#ffa8B6',
        'secondary': '#64748b',
    },
    'condolence': {
        'primary': '#6c757d',  # grey
        'secondary': '#495057',
    },
    'collection_other': {
        'primary': '#7492b9',
        'secondary': '#64748b',
    },
}

def apply_category_default_theme(theme: 'OrganizationTheme', category: str) -> None:
    colors = CATEGORY_DEFAULT_COLORS.get(category)
    if not colors:
        return
    # Only set if not explicitly customized yet
    theme.primary_color = colors['primary']
    theme.secondary_color = colors['secondary']


class OrganizationTheme(models.Model):
    """
    Stores branding and theme customization for an organization.
    Linked 1-to-1 with Organization.
    """
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='theme')
    
    # Branding
    logo = models.ImageField(upload_to='org_logos/', blank=True, null=True, help_text='Organization logo (recommended: 200x200px)')
    favicon = models.ImageField(upload_to='org_favicons/', blank=True, null=True, help_text='Favicon (recommended: 32x32px)')
    
    # Colors (hex format, e.g., #7492B9)
    primary_color = models.CharField(max_length=7, default='#7492B9', help_text='Primary brand color (hex format)')
    secondary_color = models.CharField(max_length=7, default='#64748b', help_text='Secondary color (hex format)')
    success_color = models.CharField(max_length=7, default='#059669', help_text='Success color (hex format)')
    warning_color = models.CharField(max_length=7, default='#d97706', help_text='Warning color (hex format)')
    danger_color = models.CharField(max_length=7, default='#dc2626', help_text='Danger color (hex format)')
    
    # Typography & Branding
    navbar_title = models.CharField(max_length=255, blank=True, help_text='Custom navbar title (defaults to org name)')
    footer_text = models.TextField(blank=True, help_text='Custom footer text')
    watermark_text = models.CharField(max_length=100, default='Bossin', help_text='Watermark text for reports')
    
    # Financial Settings
    default_pledge_amount = models.DecimalField(max_digits=12, decimal_places=2, default=70000, help_text='Default pledge amount for new members (e.g., 70000)')
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, default=210000, help_text='Target collection amount for the organization (e.g., 210000)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Organization Theme'
        verbose_name_plural = 'Organization Themes'

    def __str__(self):
        return f"Theme for {self.organization.name}"


class OrganizationUser(models.Model):
    """
    Represents membership of a User in an Organization with a specific role.
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),           # Can manage org, staff, settings
        ('admin', 'Admin'),           # Can manage staff and view reports
        ('staff', 'Staff'),           # Can record transactions and view data
        ('viewer', 'Viewer'),         # Read-only access
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='staff_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='org_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('organization', 'user')
        ordering = ['organization', 'user']
        indexes = [
            models.Index(fields=['organization', 'user']),
            models.Index(fields=['organization', 'role']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.role})"

    def is_owner(self):
        return self.role == 'owner'

    def is_admin(self):
        return self.role in ['owner', 'admin']

    def is_staff_or_higher(self):
        return self.role in ['owner', 'admin', 'staff']

# ============================================================================
# EXISTING MODELS (UPDATED WITH ORGANIZATION FK)
# ============================================================================

class Member(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members', null=True, blank=True)
    name = models.CharField(max_length=200)

    pledge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('70000.00'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    paid_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    course = models.CharField(max_length=100, blank=True, null=True)
    year = models.CharField(max_length=20, blank=True, null=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('organization', 'name')
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        return self.name

    @property
    def remaining(self):
        return self.pledge - self.paid_total

    @property
    def is_complete(self):
        return self.paid_total >= self.pledge

    @property
    def is_incomplete(self):
        return 0 < self.paid_total < self.pledge

    @property
    def not_started(self):
        return self.paid_total == 0

    @property
    def has_exceeded(self):
        return self.paid_total > self.pledge

    @property
    def status_display(self):
        if self.has_exceeded:
            return "Exceeded"
        elif self.is_complete:
            return "Complete"
        elif self.is_incomplete:
            return "Incomplete"
        else:
            return "Not Started"

    def update_paid_total(self):
        total = self.transaction_set.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        self.paid_total = total
        self.save(update_fields=['paid_total', 'updated_at'])


class Transaction(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date = models.DateField()
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'date']),
            models.Index(fields=['organization', 'member']),
        ]

    def __str__(self):
        return f"{self.member.name} - {self.amount} on {self.date}"

    def save(self, *args, **kwargs):
        """Override save to update member's paid_total"""
        super().save(*args, **kwargs)
        self.member.update_paid_total()

    def delete(self, *args, **kwargs):
        """Override delete to update member's paid_total"""
        super().delete(*args, **kwargs)
        self.member.update_paid_total()


class MemberEditLog(models.Model):
    """
    Tracks all edits made to member fields (name, phone, year, paid_total).
    Used for audit trail and owner-only visibility.
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='member_edit_logs', null=True, blank=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='edit_logs')
    field_changed = models.CharField(max_length=50)  # e.g., 'name', 'phone', 'paid_total', 'year'
    before_value = models.TextField(blank=True, null=True)
    after_value = models.TextField(blank=True, null=True)
    edited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['organization', 'member']),
        ]
    
    def __str__(self):
        return f"{self.member.name} - {self.field_changed} changed by {self.edited_by.username} on {self.created_at}"


class PaymentRequest(models.Model):
    """Manual subscription payment request submitted by org; admin confirms manually."""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='payment_requests')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_requests')
    months = models.PositiveIntegerField(default=1)
    is_trial = models.BooleanField(default=False)
    amount_tzs = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = models.PositiveIntegerField(default=0)
    category_snapshot = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    reference_note = models.CharField(max_length=120, blank=True, null=True, help_text='Payer name/phone or M-Pesa ref')
    PAYMENT_METHOD_CHOICES = [
        ('mobile_payment', 'Mobile Payment'),
        ('wakala', 'Wakala/Agent'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    amount_sent = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    staff_comment = models.TextField(blank=True, null=True, help_text='Internal note by site staff (Bossin)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
        ]

    def __str__(self):
        return f"PaymentRequest({self.organization.name}, {self.months}m, {self.amount_tzs} TZS, {self.status})"

class UserProfile(models.Model):
    """
    Extended user profile for additional user information and flags.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')

    # Onboarding and profile completion
    needs_onboarding = models.BooleanField(default=False, help_text='User needs to complete onboarding (email/name collection)')
    onboarding_completed = models.BooleanField(default=False, help_text='User has completed onboarding')

    # Profile information (collected during onboarding or Google signup)
    phone = models.CharField(max_length=20, blank=True, null=True, help_text='User phone number')
    bio = models.TextField(blank=True, null=True, help_text='User bio or additional information')

    # Social authentication
    firebase_uid = models.CharField(max_length=128, blank=True, null=True, unique=True, help_text='Firebase user UID')

    # Preferences
    email_notifications = models.BooleanField(default=True, help_text='Send email notifications')
    language = models.CharField(max_length=10, default='en', help_text='Preferred language')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"Profile for {self.user.username}"

    @property
    def is_profile_complete(self):
        """Check if user has completed their profile (has email and name)"""
        return (
            self.user.email and
            (self.user.first_name or self.user.last_name) and
            self.onboarding_completed
        )


# ============================================================================
# SIGNALS
# ============================================================================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=PaymentRequest)
def update_organization_subscription_on_payment_approval(sender, instance, created, **kwargs):
    """
    Automatically update organization subscription when payment request is approved.
    This acts as a backup to the admin action and ensures updates happen even if admin action fails.
    """
    # Only process if status changed to 'approved' (not a new creation, and status is approved)
    # Check if this is an update (not creation) and status is approved
    if not created and instance.status == 'approved':
        # Get fresh organization instance (Organization is already imported at top of file)
        org = Organization.objects.get(pk=instance.organization.pk)
        now = timezone.now()
        
        # Only update if organization is not already correctly configured
        # This prevents unnecessary updates if admin action already worked
        needs_update = False
        
        # Handle paid subscription
        if instance.months and instance.months > 0:
            # Calculate what the expiration should be
            subscription_active = org.subscription_expires_at and org.subscription_expires_at > now
            
            trial_active = False
            remaining_trial_days = 0
            if org.trial_started_at:
                trial_end = org.trial_started_at + timezone.timedelta(days=7)
                if trial_end > now:
                    trial_active = True
                    remaining_trial_days = (trial_end - now).days
            
            if subscription_active:
                expected_expires = org.subscription_expires_at + timezone.timedelta(days=30*instance.months)
            elif trial_active:
                total_days = remaining_trial_days + (30 * instance.months)
                expected_expires = now + timezone.timedelta(days=total_days)
            else:
                expected_expires = now + timezone.timedelta(days=30*instance.months)
            
            # Check if update is needed
            if org.subscription_status != 'SUBSCRIBED' or not org.subscription_expires_at or org.subscription_expires_at != expected_expires:
                needs_update = True
                org.subscription_expires_at = expected_expires
                org.subscription_status = 'SUBSCRIBED'
        
        # Handle trial activation
        elif instance.is_trial:
            if not org.trial_started_at or org.subscription_status != 'FREE_TRIAL':
                needs_update = True
                if not org.trial_started_at:
                    org.trial_started_at = now
                org.subscription_status = 'FREE_TRIAL'
        
        # Save only if update is needed
        if needs_update:
            org.save()


# ============================================================================
# BOSSIN ADMIN PORTAL MODELS
# ============================================================================

class SystemSettings(models.Model):
    """
    Global system settings for Bossin platform (managed by superusers).
    Stores default prices, discount rules, payment settings, etc.
    """
    # Pricing
    base_price_tzs = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('19800.00'),
        help_text='Base monthly subscription price in TZS'
    )
    
    # Category Discounts (stored as JSON)
    category_discounts = models.JSONField(
        default=dict,
        help_text='Discount percentages per category (e.g., {"religious": 50, "organization": 35})'
    )
    
    # Payment Settings
    mpesa_number = models.CharField(
        max_length=20, 
        default='68256127',
        help_text='M-Pesa Lipa Namba'
    )
    mpesa_account_name = models.CharField(
        max_length=255, 
        default='MIPT SOFTWARES',
        help_text='M-Pesa account name'
    )
    
    # Support & Contact
    support_email = models.EmailField(
        default='support@bossin.com',
        help_text='Support contact email'
    )
    support_phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text='Support phone number'
    )
    
    # Backup Settings
    backup_enabled = models.BooleanField(
        default=True,
        help_text='Enable automatic daily backups'
    )
    backup_retention_days = models.PositiveIntegerField(
        default=30,
        help_text='Number of days to keep backups'
    )
    backup_location = models.CharField(
        max_length=500,
        default='backups',
        help_text='Backup storage location (local path or cloud bucket)'
    )
    
    # System Info
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return 'Bossin System Settings'
    
    @classmethod
    def get_settings(cls):
        """Get or create system settings singleton."""
        settings, created = cls.objects.get_or_create(pk=1)
        # Initialize default category discounts if empty
        if not settings.category_discounts:
            settings.category_discounts = {
                'organization': 35,
                'religious': 50,
                'wedding_sendoff': 35,
                'ceremonies': 35,
                'condolence': 35,
                'collection_other': 35,
            }
            settings.save()
        return settings
    
    def get_category_discount(self, category):
        """Get discount percentage for a category."""
        return self.category_discounts.get(category, 35)  # Default 35%
