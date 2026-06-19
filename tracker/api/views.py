"""API views for Bossin Finance mobile application."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from tracker.models import (
    Member,
    Transaction,
    Organization,
    OrganizationUser,
    MemberEditLog,
    PaymentRequest,
    SystemSettings,
)
from tracker.api.mixins import TenantMixin, APIResponseMixin
from tracker.api.permissions import (
    IsOrgMember,
    IsOrgStaff,
    IsOrgAdmin,
    IsOrgOwner,
    CanRecordTransactions,
    ReadOnlyForViewer,
    SubscriptionActive,
)
from tracker.api.serializers import (
    UserSerializer,
    OrganizationSerializer,
    OrganizationUpdateSerializer,
    OrganizationThemeSerializer,
    OrganizationThemeUpdateSerializer,
    OrganizationMembershipSerializer,
    MemberSerializer,
    TransactionSerializer,
    RecordPaymentSerializer,
    BulkPaymentSerializer,
    MemberEditLogSerializer,
    StaffSerializer,
    AddStaffSerializer,
    UpdateStaffSerializer,
    PaymentRequestSerializer,
    CreatePaymentRequestSerializer,
    LoginSerializer,
    RegisterSerializer,
    StaffOnboardingSerializer,
)
from tracker.api.utils import (
    get_dashboard_stats,
    filter_members_queryset,
    get_subscription_pricing,
    calculate_subscription_amount,
    check_subscription_active,
    success_response,
    error_response,
)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# =============================================================================
# AUTH ENDPOINTS
# =============================================================================

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return self._error_response(serializer.errors)

        user = serializer.validated_data['user']
        default_org = serializer.validated_data['default_org']
        tokens = get_tokens_for_user(user)

        memberships = OrganizationUser.objects.filter(
            user=user, is_active=True,
        ).select_related('organization', 'organization__theme')

        return self._success_response({
            'tokens': tokens,
            'user': UserSerializer(user).data,
            'default_org': OrganizationSerializer(
                default_org, context={'request': request},
            ).data,
            'organizations': OrganizationSerializer(
                [m.organization for m in memberships],
                many=True,
                context={'request': request},
            ).data,
        })

    def _success_response(self, data, status_code=200):
        from tracker.api.utils import success_response
        return success_response(data, status=status_code)

    def _error_response(self, errors, status_code=400):
        from tracker.api.utils import error_response
        return error_response(errors, status=status_code)


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        result = serializer.save()
        user = result['user']
        organization = result['organization']
        tokens = get_tokens_for_user(user)

        return success_response({
            'tokens': tokens,
            'user': UserSerializer(user).data,
            'organization': OrganizationSerializer(
                organization, context={'request': request},
            ).data,
        }, status=status.HTTP_201_CREATED)


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = OrganizationUser.objects.filter(
            user=request.user, is_active=True,
        ).select_related('organization', 'organization__theme')

        return success_response({
            'user': UserSerializer(request.user).data,
            'organizations': OrganizationSerializer(
                [m.organization for m in memberships],
                many=True,
                context={'request': request},
            ).data,
            'memberships': [
                {
                    'organization_slug': m.organization.slug,
                    'organization_name': m.organization.name,
                    'role': m.role,
                }
                for m in memberships
            ],
        })


class StaffOnboardingAPIView(TenantMixin, APIResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def post(self, request, org_slug):
        if request.user.userprofile.onboarding_completed:
            return self.api_error('Onboarding already completed.')

        serializer = StaffOnboardingSerializer(
            data=request.data, context={'request': request},
        )
        if not serializer.is_valid():
            return self.api_error(serializer.errors)

        request.user.email = serializer.validated_data['email']
        request.user.userprofile.phone = serializer.validated_data.get('phone', '')
        request.user.userprofile.onboarding_completed = True
        request.user.userprofile.needs_onboarding = False
        request.user.save()
        request.user.userprofile.save()

        return self.api_success({
            'user': UserSerializer(request.user).data,
            'message': 'Profile completed successfully.',
        })


class RefreshTokenAPIView(TokenRefreshView):
    """JWT token refresh - wraps simplejwt with consistent response."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return success_response({'tokens': response.data})
        return error_response(response.data, status=response.status_code)


# =============================================================================
# ORGANIZATION ENDPOINTS
# =============================================================================

class OrganizationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = OrganizationUser.objects.filter(
            user=request.user, is_active=True,
        ).select_related('organization', 'organization__theme')

        return success_response({
            'organizations': OrganizationSerializer(
                [m.organization for m in memberships],
                many=True,
                context={'request': request},
            ).data,
        })


class OrganizationDetailAPIView(TenantMixin, APIResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request, org_slug):
        return self.api_success(
            OrganizationSerializer(
                request.tenant, context={'request': request},
            ).data,
        )

    def patch(self, request, org_slug):
        if not IsOrgAdmin().has_permission(request, self):
            return self.api_error('You do not have admin permissions.', status=403)

        serializer = OrganizationUpdateSerializer(
            request.tenant, data=request.data, partial=True,
        )
        if not serializer.is_valid():
            return self.api_error(serializer.errors)
        serializer.save()
        return self.api_success(
            OrganizationSerializer(
                request.tenant, context={'request': request},
            ).data,
        )


class OrganizationThemeAPIView(TenantMixin, APIResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request, org_slug):
        return self.api_success(
            OrganizationThemeSerializer(
                request.tenant.theme, context={'request': request},
            ).data,
        )

    def patch(self, request, org_slug):
        if not IsOrgAdmin().has_permission(request, self):
            return self.api_error('You do not have admin permissions.', status=403)

        serializer = OrganizationThemeUpdateSerializer(
            request.tenant.theme, data=request.data, partial=True,
            context={'request': request},
        )
        if not serializer.is_valid():
            return self.api_error(serializer.errors)
        serializer.save()
        return self.api_success(
            OrganizationThemeSerializer(
                request.tenant.theme, context={'request': request},
            ).data,
        )


# =============================================================================
# DASHBOARD
# =============================================================================

class DashboardStatsAPIView(TenantMixin, APIResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request, org_slug):
        search = request.query_params.get('search', '')
        status_filter = request.query_params.get('filter', '')

        members_qs = Member.objects.filter(
            organization=request.tenant, is_active=True,
        )
        members_qs = filter_members_queryset(members_qs, search, status_filter)
        stats = get_dashboard_stats(request.tenant, members_qs)

        return self.api_success(stats)


# =============================================================================
# MEMBERS
# =============================================================================

class MemberListCreateAPIView(TenantMixin, APIResponseMixin, generics.ListCreateAPIView):
    serializer_class = MemberSerializer
    permission_classes = [
        IsAuthenticated, IsOrgMember, ReadOnlyForViewer,
        SubscriptionActive,
    ]

    def get_queryset(self):
        qs = Member.objects.filter(
            organization=self.request.tenant, is_active=True,
        ).order_by('name')
        search = self.request.query_params.get('search', '')
        status_filter = self.request.query_params.get('filter', '')
        return filter_members_queryset(qs, search, status_filter)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['organization'] = self.request.tenant
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'data': serializer.data,
                'error': None,
            })

        serializer = self.get_serializer(queryset, many=True)
        return self.api_success(serializer.data)

    def create(self, request, *args, **kwargs):
        if not IsOrgStaff().has_permission(request, self):
            return self.api_error('You do not have staff permissions.', status=403)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return self.api_error(serializer.errors)

        member = serializer.save(organization=request.tenant)
        return self.api_success(
            MemberSerializer(member).data,
            status=status.HTTP_201_CREATED,
        )


class MemberDetailAPIView(TenantMixin, APIResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MemberSerializer
    permission_classes = [
        IsAuthenticated, IsOrgMember, ReadOnlyForViewer,
        SubscriptionActive,
    ]
    lookup_url_kwarg = 'member_id'

    def get_queryset(self):
        return Member.objects.filter(organization=self.request.tenant)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['organization'] = self.request.tenant
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return self.api_success(MemberSerializer(instance).data)

    def update(self, request, *args, **kwargs):
        if not IsOrgStaff().has_permission(request, self):
            return self.api_error('You do not have staff permissions.', status=403)

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_values = {
            field: str(getattr(instance, field, ''))
            for field in ['name', 'phone', 'email', 'course', 'year', 'pledge']
        }

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return self.api_error(serializer.errors)

        member = serializer.save()

        for field in old_values:
            new_val = str(getattr(member, field, ''))
            if old_values[field] != new_val:
                MemberEditLog.objects.create(
                    organization=request.tenant,
                    member=member,
                    field_changed=field,
                    before_value=old_values[field],
                    after_value=new_val,
                    edited_by=request.user,
                )

        return self.api_success(MemberSerializer(member).data)

    def destroy(self, request, *args, **kwargs):
        if not IsOrgStaff().has_permission(request, self):
            return self.api_error('You do not have staff permissions.', status=403)

        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return self.api_success({'message': 'Member deactivated successfully.'})


class MemberTransactionsAPIView(TenantMixin, APIResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request, org_slug, member_id):
        member = get_object_or_404(Member, id=member_id, organization=request.tenant)
        transactions = Transaction.objects.filter(
            member=member, organization=request.tenant,
        ).select_related('added_by').order_by('-date', '-created_at')

        return self.api_success(
            TransactionSerializer(transactions, many=True).data,
        )

    def post(self, request, org_slug, member_id):
        if not CanRecordTransactions().has_permission(request, self):
            return self.api_error('You do not have permission to record transactions.', status=403)

        sub_check = self.check_subscription_or_respond()
        if sub_check:
            return sub_check

        member = get_object_or_404(Member, id=member_id, organization=request.tenant)
        serializer = RecordPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return self.api_error(serializer.errors)

        payment_date = serializer.validated_data.get('date') or timezone.now().date()
        transaction = Transaction.objects.create(
            organization=request.tenant,
            member=member,
            amount=serializer.validated_data['amount'],
            date=payment_date,
            added_by=request.user,
            note=serializer.validated_data.get('note', ''),
        )
        member.refresh_from_db()

        return self.api_success({
            'transaction': TransactionSerializer(transaction).data,
            'member': MemberSerializer(member).data,
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# TRANSACTIONS
# =============================================================================

class TransactionListAPIView(TenantMixin, APIResponseMixin, generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def get_queryset(self):
        qs = Transaction.objects.filter(
            organization=self.request.tenant,
        ).select_related('member', 'added_by').order_by('-date', '-created_at')

        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        member_id = self.request.query_params.get('member_id')
        added_by = self.request.query_params.get('added_by')

        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if member_id:
            qs = qs.filter(member_id=member_id)
        if added_by:
            qs = qs.filter(added_by_id=added_by)

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'data': serializer.data,
                'error': None,
            })
        serializer = self.get_serializer(queryset, many=True)
        return self.api_success(serializer.data)


class TransactionDetailAPIView(TenantMixin, APIResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, IsOrgAdmin, SubscriptionActive]
    lookup_url_kwarg = 'transaction_id'

    def get_queryset(self):
        return Transaction.objects.filter(organization=self.request.tenant)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return self.api_success(TransactionSerializer(instance).data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return self.api_error(serializer.errors)
        transaction = serializer.save()
        return self.api_success(TransactionSerializer(transaction).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return self.api_success({'message': 'Transaction deleted successfully.'})


class BulkPaymentAPIView(TenantMixin, APIResponseMixin, APIView):
    """Record multiple daily collection payments at once."""

    permission_classes = [IsAuthenticated, CanRecordTransactions, SubscriptionActive]

    def post(self, request, org_slug):
        serializer = BulkPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return self.api_error(serializer.errors)

        results = []
        errors = []
        today = timezone.now().date()

        for payment in serializer.validated_data['payments']:
            try:
                member = Member.objects.get(
                    id=payment['member_id'],
                    organization=request.tenant,
                    is_active=True,
                )
                transaction = Transaction.objects.create(
                    organization=request.tenant,
                    member=member,
                    amount=payment['payment_amount'],
                    date=today,
                    added_by=request.user,
                    note=payment.get('note', ''),
                )
                member.refresh_from_db()
                results.append({
                    'transaction_id': transaction.id,
                    'member': MemberSerializer(member).data,
                })
            except Member.DoesNotExist:
                errors.append({
                    'member_id': payment['member_id'],
                    'error': 'Member not found.',
                })
            except Exception as e:
                errors.append({
                    'member_id': payment['member_id'],
                    'error': str(e),
                })

        return self.api_success({
            'recorded': results,
            'errors': errors,
            'success_count': len(results),
            'error_count': len(errors),
        })


# =============================================================================
# STAFF MANAGEMENT
# =============================================================================

class StaffListCreateAPIView(TenantMixin, APIResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def get(self, request, org_slug):
        staff = OrganizationUser.objects.filter(
            organization=request.tenant,
        ).select_related('user', 'user__userprofile').order_by('role', 'user__username')

        return self.api_success(StaffSerializer(staff, many=True).data)

    def post(self, request, org_slug):
        serializer = AddStaffSerializer(data=request.data)
        if not serializer.is_valid():
            return self.api_error(serializer.errors)

        data = serializer.validated_data
        if User.objects.filter(username=data['username']).exists():
            return self.api_error('Username already exists.')

        user = User.objects.create_user(
            username=data['username'],
            email=data.get('email', ''),
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
        )
        user.userprofile.needs_onboarding = True
        user.userprofile.save()

        org_user = OrganizationUser.objects.create(
            user=user,
            organization=request.tenant,
            role=data['role'],
            is_active=True,
        )

        return self.api_success(
            StaffSerializer(org_user).data,
            status=status.HTTP_201_CREATED,
        )


class StaffDetailAPIView(TenantMixin, APIResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def patch(self, request, org_slug, staff_id):
        org_user = get_object_or_404(
            OrganizationUser, id=staff_id, organization=request.tenant,
        )
        if org_user.role == 'owner':
            return self.api_error('Cannot modify organization owner.', status=403)

        serializer = UpdateStaffSerializer(data=request.data)
        if not serializer.is_valid():
            return self.api_error(serializer.errors)

        if 'role' in serializer.validated_data:
            org_user.role = serializer.validated_data['role']
        if 'is_active' in serializer.validated_data:
            org_user.is_active = serializer.validated_data['is_active']
        org_user.save()

        return self.api_success(StaffSerializer(org_user).data)

    def delete(self, request, org_slug, staff_id):
        org_user = get_object_or_404(
            OrganizationUser, id=staff_id, organization=request.tenant,
        )
        if org_user.role == 'owner':
            return self.api_error('Cannot remove organization owner.', status=403)

        org_user.is_active = False
        org_user.save()
        return self.api_success({'message': 'Staff member deactivated.'})


# =============================================================================
# AUDIT LOG
# =============================================================================

class MemberEditLogAPIView(TenantMixin, APIResponseMixin, generics.ListAPIView):
    serializer_class = MemberEditLogSerializer
    permission_classes = [IsAuthenticated, IsOrgOwner]

    def get_queryset(self):
        return MemberEditLog.objects.filter(
            organization=self.request.tenant,
        ).select_related('member', 'edited_by').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'data': serializer.data,
                'error': None,
            })
        serializer = self.get_serializer(queryset, many=True)
        return self.api_success(serializer.data)


# =============================================================================
# SUBSCRIPTION & BILLING
# =============================================================================

class SubscriptionStatusAPIView(TenantMixin, APIResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request, org_slug):
        is_active, status_info = check_subscription_active(request.tenant)
        pricing = get_subscription_pricing(request.tenant)

        pending = PaymentRequest.objects.filter(
            organization=request.tenant,
            submitted_by=request.user,
            status='pending',
        ).order_by('-created_at').first()

        recent_requests = PaymentRequest.objects.filter(
            organization=request.tenant,
            submitted_by=request.user,
        ).order_by('-created_at')[:10]

        return self.api_success({
            'subscription': status_info,
            'pricing': pricing,
            'pending_request': (
                PaymentRequestSerializer(pending).data if pending else None
            ),
            'recent_requests': PaymentRequestSerializer(
                recent_requests, many=True,
            ).data,
        })


class PaymentRequestCreateAPIView(TenantMixin, APIResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def post(self, request, org_slug):
        serializer = CreatePaymentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return self.api_error(serializer.errors)

        months = serializer.validated_data['months']
        total_amount, discount = calculate_subscription_amount(
            months, request.tenant,
        )

        payment_request = PaymentRequest.objects.create(
            organization=request.tenant,
            submitted_by=request.user,
            months=months,
            is_trial=False,
            amount_tzs=total_amount,
            discount_percent=discount,
            category_snapshot=request.tenant.category,
            reference_note=serializer.validated_data.get('reference_note'),
            payment_method=serializer.validated_data.get('payment_method'),
            amount_sent=serializer.validated_data.get('amount_sent'),
        )

        return self.api_success(
            PaymentRequestSerializer(payment_request).data,
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# SYSTEM / HEALTH
# =============================================================================

class HealthCheckAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db import connection

        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
        except Exception:
            db_ok = False

        return success_response({
            'status': 'healthy' if db_ok else 'unhealthy',
            'database': 'connected' if db_ok else 'disconnected',
            'timestamp': timezone.now().isoformat(),
            'version': '1.0.0',
        })


class HelpInfoAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        settings = SystemSettings.get_settings()
        return success_response({
            'support_email': settings.support_email,
            'support_phone': settings.support_phone,
            'mpesa_number': settings.mpesa_number,
            'mpesa_account_name': settings.mpesa_account_name,
            'whatsapp_number': '+255614021404',
        })
