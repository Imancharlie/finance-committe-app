"""DRF serializers for the Bossin Finance API."""

from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from tracker.models import (
    Member,
    Transaction,
    Organization,
    OrganizationTheme,
    OrganizationUser,
    MemberEditLog,
    PaymentRequest,
    UserProfile,
    SystemSettings,
    apply_category_default_theme,
)
from tracker.permissions import get_user_org_role


class UserSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()
    needs_onboarding = serializers.SerializerMethodField()
    onboarding_completed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'needs_onboarding', 'onboarding_completed',
        ]
        read_only_fields = fields

    def get_phone(self, obj):
        try:
            return obj.userprofile.phone
        except UserProfile.DoesNotExist:
            return None

    def get_needs_onboarding(self, obj):
        try:
            return obj.userprofile.needs_onboarding
        except UserProfile.DoesNotExist:
            return False

    def get_onboarding_completed(self, obj):
        try:
            return obj.userprofile.onboarding_completed
        except UserProfile.DoesNotExist:
            return False


class OrganizationThemeSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationTheme
        fields = [
            'primary_color', 'secondary_color', 'success_color',
            'warning_color', 'danger_color', 'navbar_title',
            'footer_text', 'watermark_text', 'default_pledge_amount',
            'target_amount', 'logo_url',
        ]

    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None


class OrganizationSerializer(serializers.ModelSerializer):
    theme = OrganizationThemeSerializer(read_only=True)
    subscription_info = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'subscription_status', 'subscription_expires_at',
            'trial_started_at', 'is_active', 'created_at',
            'theme', 'subscription_info', 'user_role',
        ]
        read_only_fields = [
            'id', 'slug', 'subscription_status', 'subscription_expires_at',
            'trial_started_at', 'created_at',
        ]

    def get_subscription_info(self, obj):
        from tracker.api.utils import check_subscription_active
        _, info = check_subscription_active(obj)
        return info

    def get_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return get_user_org_role(request.user, obj)
        return None


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['name', 'description', 'category']


class OrganizationThemeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationTheme
        fields = [
            'primary_color', 'secondary_color', 'success_color',
            'warning_color', 'danger_color', 'navbar_title',
            'footer_text', 'watermark_text', 'default_pledge_amount',
            'target_amount', 'logo',
        ]


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = OrganizationUser
        fields = ['id', 'user', 'organization', 'role', 'is_active', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class MemberSerializer(serializers.ModelSerializer):
    remaining = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    status_display = serializers.CharField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    is_incomplete = serializers.BooleanField(read_only=True)
    not_started = serializers.BooleanField(read_only=True)
    has_exceeded = serializers.BooleanField(read_only=True)

    class Meta:
        model = Member
        fields = [
            'id', 'name', 'pledge', 'paid_total', 'remaining',
            'phone', 'email', 'course', 'year', 'is_active',
            'status_display', 'is_complete', 'is_incomplete',
            'not_started', 'has_exceeded', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'paid_total', 'created_at', 'updated_at']

    def validate_pledge(self, value):
        if value <= 0:
            raise serializers.ValidationError('Pledge must be greater than zero.')
        return value

    def validate(self, attrs):
        organization = self.context.get('organization')
        name = attrs.get('name', getattr(self.instance, 'name', None))
        if organization and name:
            qs = Member.objects.filter(organization=organization, name__iexact=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'name': 'A member with this name already exists.'})
        return attrs


class TransactionSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)
    added_by_username = serializers.CharField(source='added_by.username', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'member', 'member_name', 'amount', 'date',
            'note', 'added_by', 'added_by_username',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'added_by', 'added_by_username', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        if value > Decimal('10000000'):
            raise serializers.ValidationError('Amount cannot exceed 10,000,000 TZS.')
        return value

    def validate_note(self, value):
        if value and len(value) > 500:
            raise serializers.ValidationError('Note cannot exceed 500 characters.')
        return value


class RecordPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    date = serializers.DateField(required=False)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Payment amount must be greater than zero.')
        return value


class BulkPaymentItemSerializer(serializers.Serializer):
    member_id = serializers.IntegerField()
    payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class BulkPaymentSerializer(serializers.Serializer):
    payments = BulkPaymentItemSerializer(many=True)

    def validate_payments(self, value):
        if not value:
            raise serializers.ValidationError('At least one payment is required.')
        return value


class MemberEditLogSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)
    edited_by_username = serializers.CharField(source='edited_by.username', read_only=True)

    class Meta:
        model = MemberEditLog
        fields = [
            'id', 'member', 'member_name', 'field_changed',
            'before_value', 'after_value', 'edited_by',
            'edited_by_username', 'created_at',
        ]
        read_only_fields = fields


class StaffUserSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone']

    def get_phone(self, obj):
        try:
            return obj.userprofile.phone
        except UserProfile.DoesNotExist:
            return None


class StaffSerializer(serializers.ModelSerializer):
    user = StaffUserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = OrganizationUser
        fields = ['id', 'user', 'user_id', 'role', 'is_active', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class AddStaffSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=['admin', 'staff', 'viewer'], default='staff')


class UpdateStaffSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['admin', 'staff', 'viewer'], required=False)
    is_active = serializers.BooleanField(required=False)


class PaymentRequestSerializer(serializers.ModelSerializer):
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)

    class Meta:
        model = PaymentRequest
        fields = [
            'id', 'months', 'is_trial', 'amount_tzs', 'discount_percent',
            'category_snapshot', 'status', 'reference_note', 'payment_method',
            'amount_sent', 'submitted_by', 'submitted_by_username',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'amount_tzs', 'discount_percent', 'category_snapshot',
            'status', 'submitted_by', 'submitted_by_username',
            'created_at', 'updated_at',
        ]


class CreatePaymentRequestSerializer(serializers.Serializer):
    months = serializers.IntegerField(min_value=1, max_value=12, default=1)
    reference_note = serializers.CharField(required=False, allow_blank=True, max_length=120)
    payment_method = serializers.ChoiceField(
        choices=['mobile_payment', 'wakala'],
        required=False,
        allow_blank=True,
    )
    amount_sent = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True,
    )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs['username'],
            password=attrs['password'],
        )
        if not user:
            raise serializers.ValidationError('Invalid username or password.')

        org_user = OrganizationUser.objects.filter(user=user, is_active=True).first()
        if not org_user:
            raise serializers.ValidationError(
                'Your account is not active in any organization. Please contact your administrator.'
            )

        attrs['user'] = user
        attrs['default_org'] = org_user.organization
        return attrs


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    organization_name = serializers.CharField(max_length=255)
    organization_description = serializers.CharField(required=False, allow_blank=True)
    accept_terms = serializers.BooleanField()

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('This email is already registered.')
        return value

    def validate_organization_name(self, value):
        if Organization.objects.filter(name=value).exists():
            raise serializers.ValidationError('An organization with this name already exists.')
        return value

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError('You must accept the Terms & Conditions.')
        return value

    def create(self, validated_data):
        validated_data.pop('accept_terms')

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )

        org_slug = slugify(validated_data['organization_name'])
        base_slug = org_slug
        counter = 1
        while Organization.objects.filter(slug=org_slug).exists():
            org_slug = f"{base_slug}-{counter}"
            counter += 1

        organization = Organization.objects.create(
            name=validated_data['organization_name'],
            slug=org_slug,
            description=validated_data.get('organization_description', ''),
            is_active=True,
            trial_started_at=timezone.now(),
            subscription_status='FREE_TRIAL',
        )

        theme = OrganizationTheme.objects.create(
            organization=organization,
            primary_color='#7492b9',
            secondary_color='#6c757d',
            success_color='#28a745',
            warning_color='#ffc107',
            danger_color='#dc3545',
            navbar_title=organization.name,
            watermark_text='Bossin',
            default_pledge_amount=Decimal('70000.00'),
            target_amount=Decimal('210000.00'),
        )
        apply_category_default_theme(theme, organization.category)
        theme.save()

        OrganizationUser.objects.create(
            user=user,
            organization=organization,
            role='owner',
            is_active=True,
        )

        return {'user': user, 'organization': organization}


class StaffOnboardingSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError('This email is already in use by another account.')
        return value


class DashboardStatsSerializer(serializers.Serializer):
    total_collected = serializers.CharField()
    total_pledged = serializers.CharField()
    target_amount = serializers.CharField()
    progress_percentage = serializers.FloatField()
    member_count = serializers.IntegerField()
    not_paid_count = serializers.IntegerField()
    incomplete_count = serializers.IntegerField()
    complete_count = serializers.IntegerField()
    exceeded_count = serializers.IntegerField()


class HelpInfoSerializer(serializers.Serializer):
    support_email = serializers.CharField()
    support_phone = serializers.CharField(allow_null=True)
    mpesa_number = serializers.CharField()
    mpesa_account_name = serializers.CharField()
