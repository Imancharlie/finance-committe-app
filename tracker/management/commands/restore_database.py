"""
Django management command to restore the database from a backup.

Usage:
    python manage.py restore_database backups/db_backup_20251105_043055.sqlite3.gz
    python manage.py restore_database backups/db_backup_20251105_043055.sqlite3.gz --no-input
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pathlib import Path
import shutil
import gzip
import os
import sys


class Command(BaseCommand):
    help = 'Restore the database from a backup file'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_path',
            type=str,
            help='Path to the backup file (.sqlite3 or .sqlite3.gz)'
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Skip confirmation prompt'
        )
        parser.add_argument(
            '--create-backup',
            action='store_true',
            default=True,
            help='Create backup of current database before restoring (default: True)'
        )

    def handle(self, *args, **options):
        backup_path = Path(options['backup_path'])
        
        # Check if backup file exists
        if not backup_path.exists():
            raise CommandError(f'Backup file not found: {backup_path}')
        
        # Get database path
        db_config = settings.DATABASES['default']
        db_engine = db_config.get('ENGINE', '')
        
        if 'sqlite' in db_engine.lower():
            self.restore_sqlite(db_config, backup_path, options)
        elif 'postgresql' in db_engine.lower():
            self.stdout.write(
                self.style.ERROR('PostgreSQL restore not yet implemented. Use pg_restore manually.')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'Unsupported database engine: {db_engine}')
            )

    def restore_sqlite(self, db_config, backup_path, options):
        """Restore SQLite database from backup."""
        db_path = Path(db_config['NAME'])
        
        # Confirm restoration
        if not options['no_input']:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠️  WARNING: This will replace your current database!'
                )
            )
            self.stdout.write(f'Current database: {db_path}')
            self.stdout.write(f'Backup file: {backup_path}')
            
            if db_path.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'Current database size: {db_path.stat().st_size / (1024*1024):.2f} MB'
                    )
                )
            
            confirm = input('\nDo you want to continue? (yes/no): ')
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write(self.style.ERROR('Restore cancelled.'))
                return
        
        try:
            # Create backup of current database if it exists
            if options['create_backup'] and db_path.exists():
                backup_dir = backup_path.parent
                timestamp = self.get_timestamp()
                current_backup = backup_dir / f'pre_restore_backup_{timestamp}.sqlite3.gz'
                
                self.stdout.write(f'Creating backup of current database...')
                with open(db_path, 'rb') as f_in:
                    with gzip.open(current_backup, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Current database backed up to: {current_backup}')
                )
            
            # Determine if backup is compressed
            is_compressed = backup_path.suffix == '.gz' or backup_path.name.endswith('.gz')
            
            # Extract/restore database
            if is_compressed:
                self.stdout.write(f'Decompressing backup file...')
                temp_db_path = db_path.parent / f'{db_path.name}.restore_temp'
                
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Replace database
                if db_path.exists():
                    db_path.unlink()
                
                shutil.move(temp_db_path, db_path)
                self.stdout.write(f'✓ Database restored from compressed backup')
            else:
                # Direct copy
                if db_path.exists():
                    db_path.unlink()
                
                shutil.copy2(backup_path, db_path)
                self.stdout.write(f'✓ Database restored from backup')
            
            # Verify restoration
            if db_path.exists():
                file_size = db_path.stat().st_size / (1024 * 1024)  # MB
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓✓✓ RESTORE SUCCESSFUL! ✓✓✓\n'
                        f'Database restored: {db_path}\n'
                        f'Size: {file_size:.2f} MB'
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        '\n⚠️  IMPORTANT: You may need to restart your Django server!'
                    )
                )
            else:
                raise CommandError('Restore failed: Database file not found after restore')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error restoring database: {str(e)}')
            )
            raise CommandError(f'Restore failed: {str(e)}')

    def get_timestamp(self):
        """Get current timestamp for backup naming."""
        from django.utils import timezone
        return timezone.now().strftime('%Y%m%d_%H%M%S')

