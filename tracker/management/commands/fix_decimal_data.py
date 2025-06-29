from django.core.management.base import BaseCommand
from django.db import connection
from decimal import Decimal, InvalidOperation
from tracker.models import Member, Transaction


class Command(BaseCommand):
    help = 'Fix invalid decimal values in the database'

    def handle(self, *args, **options):
        self.stdout.write('Starting database decimal fix...')
        
        # Fix Member table
        self.fix_member_decimals()
        
        # Fix Transaction table
        self.fix_transaction_decimals()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully fixed decimal values in database')
        )

    def fix_member_decimals(self):
        """Fix invalid decimal values in Member table"""
        self.stdout.write('Fixing Member table decimals...')
        
        with connection.cursor() as cursor:
            # Get all members with potential decimal issues
            cursor.execute("""
                SELECT id, name, pledge, paid_total 
                FROM tracker_member
            """)
            
            members = cursor.fetchall()
            fixed_count = 0
            
            for member_id, name, pledge, paid_total in members:
                try:
                    # Try to convert to Decimal
                    if pledge is not None:
                        Decimal(str(pledge))
                    if paid_total is not None:
                        Decimal(str(paid_total))
                except (InvalidOperation, ValueError, TypeError):
                    # Fix the invalid values
                    try:
                        member = Member.objects.get(id=member_id)
                        
                        # Fix pledge
                        if pledge is None or str(pledge).strip() == '':
                            member.pledge = Decimal('70000.00')
                        else:
                            try:
                                member.pledge = Decimal(str(pledge).replace(',', '').strip())
                            except:
                                member.pledge = Decimal('70000.00')
                        
                        # Fix paid_total
                        if paid_total is None or str(paid_total).strip() == '':
                            member.paid_total = Decimal('0.00')
                        else:
                            try:
                                member.paid_total = Decimal(str(paid_total).replace(',', '').strip())
                            except:
                                member.paid_total = Decimal('0.00')
                        
                        member.save()
                        fixed_count += 1
                        self.stdout.write(f'Fixed member: {name}')
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error fixing member {name}: {str(e)}')
                        )
            
            self.stdout.write(f'Fixed {fixed_count} members')

    def fix_transaction_decimals(self):
        """Fix invalid decimal values in Transaction table"""
        self.stdout.write('Fixing Transaction table decimals...')
        
        with connection.cursor() as cursor:
            # Get all transactions with potential decimal issues
            cursor.execute("""
                SELECT id, amount 
                FROM tracker_transaction
            """)
            
            transactions = cursor.fetchall()
            fixed_count = 0
            
            for transaction_id, amount in transactions:
                try:
                    # Try to convert to Decimal
                    if amount is not None:
                        Decimal(str(amount))
                except (InvalidOperation, ValueError, TypeError):
                    # Fix the invalid values
                    try:
                        transaction = Transaction.objects.get(id=transaction_id)
                        
                        # Fix amount
                        if amount is None or str(amount).strip() == '':
                            transaction.amount = Decimal('0.00')
                        else:
                            try:
                                transaction.amount = Decimal(str(amount).replace(',', '').strip())
                            except:
                                transaction.amount = Decimal('0.00')
                        
                        transaction.save()
                        fixed_count += 1
                        self.stdout.write(f'Fixed transaction ID: {transaction_id}')
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error fixing transaction {transaction_id}: {str(e)}')
                        )
            
            self.stdout.write(f'Fixed {fixed_count} transactions') 