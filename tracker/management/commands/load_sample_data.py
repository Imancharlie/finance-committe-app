from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tracker.models import Member, Transaction
from decimal import Decimal
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Load sample data for testing the Mission Offering Tracker'

    def handle(self, *args, **options):
        self.stdout.write('Loading sample data...')
        
        # Create admin user if it doesn't exist
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write('Created admin user: admin/admin123')
        
        # Sample member names
        sample_names = [
            'John Mwambene',
            'Sarah Kimambo',
            'Michael Mwakasege',
            'Grace Mwakatobe',
            'David Mwambene',
            'Elizabeth Mwakasege',
            'Peter Mwakatobe',
            'Mary Kimambo',
            'James Mwambene',
            'Anna Mwakasege',
            'Robert Mwakatobe',
            'Helen Kimambo',
            'Thomas Mwambene',
            'Catherine Mwakasege',
            'Daniel Mwakatobe',
            'Ruth Kimambo',
            'Joseph Mwambene',
            'Esther Mwakasege',
            'Andrew Mwakatobe',
            'Dorothy Kimambo'
        ]
        
        # Sample courses
        courses = [
            'Computer Science',
            'Business Administration',
            'Engineering',
            'Medicine',
            'Law',
            'Education',
            'Agriculture',
            'Economics',
            'Psychology',
            'Sociology'
        ]
        
        # Create members
        members_created = 0
        for i, name in enumerate(sample_names):
            member, created = Member.objects.get_or_create(
                name=name,
                defaults={
                    'pledge': Decimal(random.choice([70000, 80000, 90000, 100000, 120000])),
                    'phone': f'07{random.randint(10000000, 99999999)}',
                    'email': f'{name.lower().replace(" ", ".")}@example.com',
                    'course': random.choice(courses),
                    'year': random.choice(['1st Year', '2nd Year', '3rd Year', '4th Year', 'Graduate'])
                }
            )
            if created:
                members_created += 1
        
        self.stdout.write(f'Created {members_created} members')
        
        # Create sample transactions
        transactions_created = 0
        for member in Member.objects.all():
            # Random number of transactions per member (0-3)
            num_transactions = random.randint(0, 3)
            
            for i in range(num_transactions):
                # Random date within last 6 months
                random_days = random.randint(0, 180)
                transaction_date = date.today() - timedelta(days=random_days)
                
                # Random amount (partial payments)
                max_amount = min(member.pledge - member.paid_total, member.pledge * Decimal('0.4'))
                if max_amount > 0:
                    amount = Decimal(random.randint(10000, int(max_amount)))
                    
                    transaction = Transaction.objects.create(
                        member=member,
                        amount=amount,
                        date=transaction_date,
                        added_by=admin_user,
                        note=random.choice([
                            'Monthly contribution',
                            'Special offering',
                            'Mission pledge payment',
                            'Additional contribution',
                            'First payment',
                            'Second installment'
                        ])
                    )
                    transactions_created += 1
        
        self.stdout.write(f'Created {transactions_created} transactions')
        
        # Update member paid totals
        for member in Member.objects.all():
            member.update_paid_total()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully loaded sample data!\n'
                f'- Admin user: admin/admin123\n'
                f'- {Member.objects.count()} members\n'
                f'- {Transaction.objects.count()} transactions\n'
                f'- Total collected: TZS {sum(m.paid_total for m in Member.objects.all()):,.2f}'
            )
        ) 