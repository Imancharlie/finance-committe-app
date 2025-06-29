from django.core.management.base import BaseCommand
from django.db import connection
from decimal import Decimal, InvalidOperation


class Command(BaseCommand):
    help = 'Clean database by fixing all decimal issues'

    def handle(self, *args, **options):
        self.stdout.write('Starting aggressive database cleanup...')
        
        with connection.cursor() as cursor:
            # Fix Member table decimals
            self.stdout.write('Fixing Member table...')
            
            # Update all problematic pledge values
            cursor.execute("""
                UPDATE tracker_member 
                SET pledge = 70000.00 
                WHERE pledge IS NULL OR pledge = '' OR pledge = 'None'
            """)
            
            # Update all problematic paid_total values
            cursor.execute("""
                UPDATE tracker_member 
                SET paid_total = 0.00 
                WHERE paid_total IS NULL OR paid_total = '' OR paid_total = 'None'
            """)
            
            # Fix any non-numeric values in pledge
            cursor.execute("""
                UPDATE tracker_member 
                SET pledge = 70000.00 
                WHERE pledge NOT LIKE '%.%' AND pledge NOT GLOB '[0-9]*'
            """)
            
            # Fix any non-numeric values in paid_total
            cursor.execute("""
                UPDATE tracker_member 
                SET paid_total = 0.00 
                WHERE paid_total NOT LIKE '%.%' AND paid_total NOT GLOB '[0-9]*'
            """)
            
            # Fix Transaction table decimals
            self.stdout.write('Fixing Transaction table...')
            
            # Update all problematic amount values
            cursor.execute("""
                UPDATE tracker_transaction 
                SET amount = 0.00 
                WHERE amount IS NULL OR amount = '' OR amount = 'None'
            """)
            
            # Fix any non-numeric values in amount
            cursor.execute("""
                UPDATE tracker_transaction 
                SET amount = 0.00 
                WHERE amount NOT LIKE '%.%' AND amount NOT GLOB '[0-9]*'
            """)
            
            # Commit the changes
            connection.commit()
            
        self.stdout.write(
            self.style.SUCCESS('Database cleanup completed successfully!')
        ) 