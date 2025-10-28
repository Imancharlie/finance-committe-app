#!/bin/bash
# Production deployment script for Bossin Finance Committee App
# Run this script on your production server

set -e  # Exit on any error

echo "🚀 Starting Bossin App Production Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="bossin-app"
DOMAIN="yourdomain.com"  # Replace with your actual domain
EMAIL="admin@yourdomain.com"  # Replace with your email

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should not be run as root${NC}"
   exit 1
fi

echo -e "${BLUE}📋 Prerequisites Check...${NC}"

# Check if required commands are available
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}❌ Python3 is required but not installed.${NC}"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo -e "${RED}❌ pip3 is required but not installed.${NC}"; exit 1; }
command -v nginx >/dev/null 2>&1 || { echo -e "${RED}❌ nginx is required but not installed.${NC}"; exit 1; }
command -v mysql >/dev/null 2>&1 || { echo -e "${RED}❌ MySQL is required but not installed.${NC}"; exit 1; }

echo -e "${GREEN}✅ Prerequisites OK${NC}"

# Create application directory
echo -e "${BLUE}📁 Creating application directory...${NC}"
sudo mkdir -p /var/www/${APP_NAME}
sudo chown -R $USER:$USER /var/www/${APP_NAME}

# Clone or copy application code
echo -e "${BLUE}📦 Setting up application code...${NC}"
# Assuming code is already in current directory, copy to production location
cp -r . /var/www/${APP_NAME}/
cd /var/www/${APP_NAME}

# Setup Python virtual environment
echo -e "${BLUE}🐍 Setting up Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
pip install -r requirements.txt
pip install gunicorn

# Database setup
echo -e "${BLUE}🗄️ Setting up database...${NC}"
# Note: You need to manually create the database and user in MySQL
echo -e "${YELLOW}⚠️  Please ensure you have created the MySQL database and user${NC}"
echo -e "${YELLOW}⚠️  Run the following commands in MySQL:${NC}"
echo "CREATE DATABASE bossin_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo "CREATE USER 'bossin_user'@'localhost' IDENTIFIED BY 'your_secure_password';"
echo "GRANT ALL PRIVILEGES ON bossin_db.* TO 'bossin_user'@'localhost';"
echo "FLUSH PRIVILEGES;"

# Environment configuration
echo -e "${BLUE}⚙️ Setting up environment configuration...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env file with your production settings${NC}"
fi

# Run migrations
echo -e "${BLUE}🗃️ Running database migrations...${NC}"
python manage.py migrate

# Collect static files
echo -e "${BLUE}📄 Collecting static files...${NC}"
python manage.py collectstatic --noinput

# Create superuser (optional)
echo -e "${BLUE}👤 Creating superuser...${NC}"
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@yourdomain.com', 'admin123')" | python manage.py shell || echo -e "${YELLOW}⚠️  Superuser creation skipped (may already exist)${NC}"

# Setup Gunicorn
echo -e "${BLUE}🚀 Setting up Gunicorn...${NC}"
sudo tee /etc/systemd/system/${APP_NAME}.service > /dev/null <<EOF
[Unit]
Description=Bossin Finance Committee App
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=/var/www/${APP_NAME}
Environment="PATH=/var/www/${APP_NAME}/venv/bin"
ExecStart=/var/www/${APP_NAME}/venv/bin/gunicorn --workers 3 --bind unix:/var/www/${APP_NAME}/bossin.sock mission_tracker.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start ${APP_NAME}
sudo systemctl enable ${APP_NAME}

# Setup Nginx
echo -e "${BLUE}🌐 Setting up Nginx...${NC}"
sudo tee /etc/nginx/sites-available/${APP_NAME} > /dev/null <<EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /var/www/${APP_NAME}/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/${APP_NAME}/media/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/${APP_NAME}/bossin.sock;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Setup SSL with Certbot (optional)
echo -e "${BLUE}🔒 Setting up SSL certificate...${NC}"
sudo apt update
sudo apt install snapd -y
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot

# Get SSL certificate
echo -e "${YELLOW}⚠️  SSL Certificate Setup:${NC}"
echo "Run: sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
echo "Then update Nginx config for SSL redirect"

# Set proper permissions
echo -e "${BLUE}🔐 Setting proper permissions...${NC}"
sudo chown -R www-data:www-data /var/www/${APP_NAME}/media/
sudo chown -R www-data:www-data /var/www/${APP_NAME}/staticfiles/

# Create log directory
sudo mkdir -p /var/log/django
sudo chown -R www-data:www-data /var/log/django

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Edit /var/www/${APP_NAME}/.env with your production settings"
echo "2. Run: sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
echo "3. Test the application at https://${DOMAIN}"
echo "4. Monitor logs: sudo journalctl -u ${APP_NAME} -f"
echo ""
echo -e "${GREEN}🎉 Your Bossin Finance Committee App is now live!${NC}"
