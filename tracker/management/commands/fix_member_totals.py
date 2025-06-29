from django.core.management.base import BaseCommand
from django.db.models import Sum
from decimal import Decimal
from tracker.models import Member, Transaction


class Command(BaseCommand):
    help = 'Fix member paid_total values by recalculating from transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write('Starting member totals fix...')
        
        fixed_count = 0
        error_count = 0
        
        # Get all members
        members = Member.objects.all()
        total_members = members.count()
        
        self.stdout.write(f'Processing {total_members} members...')
        
        for member in members:
            try:
                # Calculate total from transactions
                transaction_total = member.transaction_set.aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0.00')
                
                # Check if current paid_total matches transaction total
                current_paid = member.paid_total or Decimal('0.00')
                
                if current_paid != transaction_total:
                    if dry_run:
                        self.stdout.write(
                            f'Would fix {member.name}: {current_paid} → {transaction_total}'
                        )
                    else:
                        member.paid_total = transaction_total
                        member.save()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Fixed {member.name}: {current_paid} → {transaction_total}'
                            )
                        )
                    fixed_count += 1
                else:
                    if not dry_run:
                        self.stdout.write(f'✓ {member.name}: {current_paid} (correct)')
                        
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error processing {member.name}: {str(e)}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN SUMMARY: Would fix {fixed_count} members')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'FIXED: {fixed_count} members')
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'ERRORS: {error_count} members could not be processed')
            )
        
        self.stdout.write('Member totals fix completed!') 