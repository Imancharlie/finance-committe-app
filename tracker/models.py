from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils.text import slugify

# ============================================================================
# MULTITENANCY MODELS
# ============================================================================

class Organization(models.Model):
    """
    Represents a tenant organization (e.g., a finance committee, church group, etc.)
    Each organization has isolated data: members, transactions, staff.
    """
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
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
