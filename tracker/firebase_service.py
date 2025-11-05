"""
Firebase Authentication Service for Django integration.
Provides Firebase authentication alongside Django's built-in auth system.
"""
import firebase_admin
from firebase_admin import auth, credentials
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import redirect
from tracker.models import OrganizationUser
import json
import os

User = get_user_model()


class FirebaseAuthService:
    """
    Service for handling Firebase Authentication integration with Django.
    """

    def __init__(self):
        """
        Initialize Firebase Admin SDK.
        """
        try:
            # Check if Firebase is already initialized
            firebase_admin.get_app()
        except ValueError:
            # Firebase not initialized, set it up
            try:
                # For production, use service account key from environment
                service_account_key = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')

                if service_account_key:
                    # Parse JSON string from environment
                    service_account_info = json.loads(service_account_key)
                    cred = credentials.Certificate(service_account_info)
                else:
                    # For development, use default credentials or skip Firebase
                    # You would typically have a service account key file
                    # cred = credentials.Certificate('path/to/serviceAccountKey.json')
                    print("Firebase service account key not found. Firebase features disabled.")
                    return

                firebase_admin.initialize_app(cred)

            except Exception as e:
                print(f"Failed to initialize Firebase: {e}")
                # Continue without Firebase if initialization fails

    def verify_firebase_token(self, id_token):
        """
        Verify Firebase ID token and return decoded token.

        Args:
            id_token (str): Firebase ID token from client

        Returns:
            dict: Decoded token data or None if invalid
        """
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            print(f"Firebase token verification failed: {e}")
            return None

    def get_or_create_user_from_firebase(self, firebase_user_data, request=None):
        """
        Get or create Django user from Firebase user data.

        Args:
            firebase_user_data (dict): Firebase user data
            request: Django request object

        Returns:
            tuple: (user, created) where created is boolean
        """
        email = firebase_user_data.get('email')
        uid = firebase_user_data.get('uid')
        display_name = firebase_user_data.get('name', '')
        first_name = firebase_user_data.get('given_name', '')
        last_name = firebase_user_data.get('family_name', '')

        if not email:
            return None, False

        # Try to get existing user
        try:
            user = User.objects.get(email=email)

            # Check if user has organization membership
            org_user = OrganizationUser.objects.filter(user=user, is_active=True).first()

            if not org_user:
                # User exists but no organization membership
                if request:
                    messages.error(request, 'Your account exists but you are not a member of any active organization. Please contact your administrator.')
                return None, False

            return user, False

        except User.DoesNotExist:
            # User doesn't exist - for organization-focused app, we don't allow open signup
            if request:
                messages.error(request, 'Account not found. Please contact your organization administrator to be added as a member.')
            return None, False

    def link_firebase_account(self, user, firebase_uid):
        """
        Link Firebase UID to Django user account.

        Args:
            user: Django User instance
            firebase_uid (str): Firebase user UID
        """
        # Store Firebase UID in user profile or custom field
        # You might want to add a firebase_uid field to UserProfile model
        try:
            user.userprofile.firebase_uid = firebase_uid
            user.userprofile.save()
        except AttributeError:
            # If UserProfile doesn't have firebase_uid field, skip
            pass

    def check_staff_onboarding_needed(self, user):
        """
        Check if staff user needs onboarding.

        Args:
            user: Django User instance

        Returns:
            bool: True if onboarding is needed
        """
        try:
            org_user = OrganizationUser.objects.filter(
                user=user,
                is_active=True,
                role__in=['staff', 'admin']
            ).first()

            if org_user and not user.has_usable_password():
                return True
        except Exception:
            pass

        return False


# Global service instance
firebase_service = FirebaseAuthService()
