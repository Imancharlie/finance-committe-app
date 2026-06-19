from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.contrib import messages
from tracker.models import OrganizationUser
from django.shortcuts import redirect

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for Google OAuth2 integration.
    Handles email-based username, organization membership checks, and staff onboarding.
    """

    def pre_social_login(self, request, sociallogin):
        """
        Called before social login.
        Check if user exists and handle organization membership.
        """
        email = sociallogin.account.extra_data.get('email')

        if not email:
            messages.error(request, 'Google account must have an email address.')
            return redirect('tracker:login')

        # Check if user already exists with this email
        try:
            user = User.objects.get(email=email)

            # Check if user has organization membership
            org_user = OrganizationUser.objects.filter(user=user, is_active=True).first()

            if not org_user:
                # User exists but no organization membership
                messages.error(request, 'Your account exists but you are not a member of any active organization. Please contact your administrator.')
                return redirect('tracker:login')

            # Connect social account to existing user
            sociallogin.connect(request, user)

        except User.DoesNotExist:
            # New user - check if they should be allowed to sign up
            # For organization-focused app, we don't allow open signup with Google
            # They need to be invited by an admin first
            messages.error(request, 'Account not found. Please contact your organization administrator to be added as a member.')
            return redirect('tracker:login')

    def save_user(self, request, sociallogin, form=None):
        """
        Save user from social login.
        Use email as username for Google accounts.
        """
        email = sociallogin.account.extra_data.get('email')
        first_name = sociallogin.account.extra_data.get('given_name', '')
        last_name = sociallogin.account.extra_data.get('family_name', '')

        # Create user with email as username
        user = sociallogin.user
        user.username = email  # Use email as username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        # Check if this is a staff member who needs onboarding
        try:
            org_user = OrganizationUser.objects.get(user=user, is_active=True)

            # If staff member has no password set (was created by admin), prompt for onboarding
            if not user.has_usable_password() and org_user.role in ['staff', 'admin']:
                # Mark user as needing onboarding
                user.userprofile.needs_onboarding = True
                user.userprofile.save()

                # Set a flag to redirect to onboarding after login
                request.session['needs_staff_onboarding'] = True
                request.session['staff_org_slug'] = org_user.organization.slug

            # Store Firebase UID if available
            firebase_uid = sociallogin.account.extra_data.get('sub') or sociallogin.account.uid
            if firebase_uid and hasattr(user, 'userprofile'):
                user.userprofile.firebase_uid = firebase_uid
                user.userprofile.save()
        except (OrganizationUser.DoesNotExist, AttributeError):
            pass

        return user

    def populate_user(self, request, sociallogin, data):
        """
        Populate user data from Google OAuth2 response.
        """
        user = super().populate_user(request, sociallogin, data)

        # Override username with email for Google accounts
        if sociallogin.account.provider == 'google':
            user.username = data.get('email', user.username)

        return user
