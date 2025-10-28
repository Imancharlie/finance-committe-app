"""
Management command to create a new organization with theme.
Usage: python manage.py create_organization --name "Organization Name" --owner username
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from tracker.models import Organization, OrganizationTheme, OrganizationUser


class Command(BaseCommand):
    help = 'Create a new organization with default theme and owner'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            required=True,
            help='Organization name'
        )
        parser.add_argument(
            '--owner',
            type=str,
            required=False,
            help='Username of the owner (optional)'
        )
        parser.add_argument(
            '--description',
            type=str,
            required=False,
            help='Organization description'
        )
        parser.add_argument(
            '--primary-color',
            type=str,
            default='#2563eb',
            help='Primary brand color (hex format, default: #2563eb)'
        )

    def handle(self, *args, **options):
        name = options['name']
        owner_username = options.get('owner')
        description = options.get('description', '')
        primary_color = options.get('primary_color', '#2563eb')

        # Check if organization already exists
        if Organization.objects.filter(name=name).exists():
            raise CommandError(f'Organization "{name}" already exists.')

        try:
            # Create organization
            org = Organization.objects.create(
                name=name,
                description=description
            )
            self.stdout.write(
                self.style.SUCCESS(f'✓ Organization "{name}" created (slug: {org.slug})')
            )

            # Create theme
            theme = OrganizationTheme.objects.create(
                organization=org,
                primary_color=primary_color,
                watermark_text='Bossin'
            )
            self.stdout.write(
                self.style.SUCCESS(f'✓ Theme created with primary color: {primary_color}')
            )

            # Add owner if provided
            if owner_username:
                try:
                    owner = User.objects.get(username=owner_username)
                    org_user = OrganizationUser.objects.create(
                        organization=org,
                        user=owner,
                        role='owner'
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ {owner_username} added as owner')
                    )
                except User.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'⚠ User "{owner_username}" not found. Please add manually.')
                    )

            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Organization setup complete!')
            )
            self.stdout.write(f'  Slug: {org.slug}')
            self.stdout.write(f'  URL: /{org.slug}/dashboard/')

        except Exception as e:
            raise CommandError(f'Error creating organization: {str(e)}')
