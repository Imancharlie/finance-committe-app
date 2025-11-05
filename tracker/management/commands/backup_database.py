"""
Django management command to backup the database.

Usage:
    python manage.py backup_database
    python manage.py backup_database --output-dir=/var/backups
    python manage.py backup_database --keep-days=30
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from pathlib import Path
import shutil
import gzip
import os
from datetime import timedelta


class Command(BaseCommand):
    help = 'Backup the database to a compressed file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directory to store backups (default: backups)'
        )
        parser.add_argument(
            '--keep-days',
            type=int,
            default=30,
            help='Number of days to keep backups (default: 30)'
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            default=True,
            help='Compress backup file (default: True)'
        )

    def handle(self, *args, **options):
        output_dir = Path(options['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get database path
        db_config = settings.DATABASES['default']
        db_engine = db_config.get('ENGINE', '')
        
        if 'sqlite' in db_engine.lower():
            self.backup_sqlite(db_config, output_dir, options)
        elif 'postgresql' in db_engine.lower():
            self.backup_postgresql(db_config, output_dir, options)
        else:
            self.stdout.write(
                self.style.ERROR(f'Unsupported database engine: {db_engine}')
            )

    def backup_sqlite(self, db_config, output_dir, options):
        """Backup SQLite database."""
        db_path = Path(db_config['NAME'])
        
        if not db_path.exists():
            self.stdout.write(
                self.style.ERROR(f'Database file not found: {db_path}')
            )
            return
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'db_backup_{timestamp}.sqlite3'
        backup_path = output_dir / backup_filename
        
        try:
            # Copy database file
            shutil.copy2(db_path, backup_path)
            self.stdout.write(f'Created backup: {backup_path}')
            
            # Compress if requested
            if options['compress']:
                compressed_path = f'{backup_path}.gz'
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove uncompressed version
                os.remove(backup_path)
                backup_path = Path(compressed_path)
                self.stdout.write(f'Compressed backup: {backup_path}')
            
            # Get file size
            file_size = backup_path.stat().st_size / (1024 * 1024)  # MB
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Backup completed: {backup_path} ({file_size:.2f} MB)'
                )
            )
            
            # Clean old backups
            self.clean_old_backups(output_dir, options['keep_days'])
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating backup: {str(e)}')
            )

    def backup_postgresql(self, db_config, output_dir, options):
        """Backup PostgreSQL database using pg_dump."""
        import subprocess
        
        db_name = db_config['NAME']
        db_user = db_config['USER']
        db_host = db_config.get('HOST', 'localhost')
        db_port = db_config.get('PORT', '5432')
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'db_backup_{timestamp}.sql'
        backup_path = output_dir / backup_filename
        
        # Build pg_dump command
        pg_dump_cmd = [
            'pg_dump',
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
            '-F', 'c',  # Custom format
            '-f', str(backup_path)
        ]
        
        try:
            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            if 'PASSWORD' in db_config:
                env['PGPASSWORD'] = db_config['PASSWORD']
            
            # Run pg_dump
            result = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Compress if requested
                if options['compress']:
                    compressed_path = f'{backup_path}.gz'
                    with open(backup_path, 'rb') as f_in:
                        with gzip.open(compressed_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    os.remove(backup_path)
                    backup_path = Path(compressed_path)
                
                file_size = backup_path.stat().st_size / (1024 * 1024)  # MB
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ PostgreSQL backup completed: {backup_path} ({file_size:.2f} MB)'
                    )
                )
                
                # Clean old backups
                self.clean_old_backups(output_dir, options['keep_days'])
            else:
                self.stdout.write(
                    self.style.ERROR(f'pg_dump failed: {result.stderr}')
                )
                
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    'pg_dump not found. Please install PostgreSQL client tools.'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating backup: {str(e)}')
            )

    def clean_old_backups(self, backup_dir, keep_days):
        """Remove backups older than keep_days."""
        cutoff_date = timezone.now() - timedelta(days=keep_days)
        deleted_count = 0
        
        # Find all backup files
        for backup_file in backup_dir.glob('db_backup_*'):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    backup_file.unlink()
                    deleted_count += 1
                    self.stdout.write(f'Deleted old backup: {backup_file.name}')
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Failed to delete {backup_file}: {e}')
                    )
        
        if deleted_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned {deleted_count} old backup(s)')
            )

