#!/bin/bash
# Complete Backup Script for Finance Committee App
# This script backs up database, media files, and important configuration

set -e  # Exit on error

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/finance-app}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
KEEP_DAYS=${KEEP_DAYS:-30}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting full backup...${NC}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Change to project directory
cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -d "iman" ]; then
    source iman/Scripts/activate 2>/dev/null || source iman/bin/activate 2>/dev/null || true
fi

# 1. Database backup
echo -e "${YELLOW}Backing up database...${NC}"
python manage.py backup_database --output-dir "$BACKUP_DIR" --keep-days "$KEEP_DAYS" || {
    echo -e "${RED}Database backup failed!${NC}"
    exit 1
}

# 2. Media files backup
echo -e "${YELLOW}Backing up media files...${NC}"
if [ -d "media" ]; then
    MEDIA_BACKUP="$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz"
    tar -czf "$MEDIA_BACKUP" -C "$PROJECT_DIR" media/ || {
        echo -e "${RED}Media backup failed!${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Media backup created: $MEDIA_BACKUP${NC}"
else
    echo -e "${YELLOW}No media directory found, skipping...${NC}"
fi

# 3. Environment files backup (if exists)
echo -e "${YELLOW}Backing up configuration files...${NC}"
if [ -f ".env" ]; then
    cp .env "$BACKUP_DIR/.env" 2>/dev/null || true
fi
if [ -f ".env.production" ]; then
    cp .env.production "$BACKUP_DIR/.env.production" 2>/dev/null || true
fi

# 4. Static files backup (if needed)
if [ -d "staticfiles" ]; then
    STATIC_BACKUP="$BACKUP_DIR/staticfiles_backup_$TIMESTAMP.tar.gz"
    tar -czf "$STATIC_BACKUP" -C "$PROJECT_DIR" staticfiles/ || true
    echo -e "${GREEN}✓ Static files backup created${NC}"
fi

# 5. Create backup manifest
echo -e "${YELLOW}Creating backup manifest...${NC}"
cat > "$BACKUP_DIR/manifest.txt" << EOF
Backup Date: $(date)
Project Directory: $PROJECT_DIR
Backup Directory: $BACKUP_DIR
Database: $(python manage.py showmigrations --plan | wc -l) migrations
EOF

# 6. Compress entire backup directory
echo -e "${YELLOW}Compressing backup archive...${NC}"
cd "$BACKUP_ROOT"
FULL_BACKUP_FILE="full_backup_$TIMESTAMP.tar.gz"
tar -czf "$FULL_BACKUP_FILE" "$(basename "$BACKUP_DIR")" || {
    echo -e "${RED}Compression failed!${NC}"
    exit 1
}

# Remove uncompressed directory
rm -rf "$BACKUP_DIR"

# Get file size
FILE_SIZE=$(du -h "$FULL_BACKUP_FILE" | cut -f1)

echo -e "${GREEN}✓ Full backup completed: $FULL_BACKUP_FILE ($FILE_SIZE)${NC}"

# 7. Clean old backups
echo -e "${YELLOW}Cleaning old backups (older than $KEEP_DAYS days)...${NC}"
find "$BACKUP_ROOT" -name "full_backup_*.tar.gz" -type f -mtime +$KEEP_DAYS -delete
echo -e "${GREEN}✓ Cleanup completed${NC}"

# 8. List recent backups
echo -e "${GREEN}Recent backups:${NC}"
ls -lh "$BACKUP_ROOT"/full_backup_*.tar.gz 2>/dev/null | tail -5 || echo "No backups found"

echo -e "${GREEN}✓ Backup process completed successfully!${NC}"

