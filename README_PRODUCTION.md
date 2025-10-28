# Bossin Finance Committee App - Production Deployment Guide

A comprehensive financial management system for committees and organizations, built with Django.

## 🚀 Features

- **Multi-Organization Support**: Each organization has isolated data and branding
- **Role-Based Access Control**: Owner, Admin, Staff, and Viewer roles
- **Member Management**: Add, edit, and track member information and payments
- **Transaction Tracking**: Record and monitor all financial transactions
- **Excel Import/Export**: Bulk import members and export data to Excel/PDF
- **Admin Dashboard**: Comprehensive admin panel with statistics
- **Progressive Web App**: Installable PWA for mobile devices
- **Responsive Design**: Works perfectly on all devices

## 🛠️ Production Deployment

### Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Python 3.8+
- MySQL 8.0+ or PostgreSQL
- Nginx
- SSL certificate (Let's Encrypt recommended)

### Quick Deployment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/bossin-app.git
   cd bossin-app
   ```

2. **Run the deployment script**:
   ```bash
   chmod +x deploy.sh
   sudo ./deploy.sh
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   nano .env  # Edit with your production settings
   ```

4. **Setup SSL certificate**:
   ```bash
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

5. **Create database**:
   ```sql
   CREATE DATABASE bossin_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'bossin_user'@'localhost' IDENTIFIED BY 'your_secure_password';
   GRANT ALL PRIVILEGES ON bossin_db.* TO 'bossin_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

### Manual Installation

If you prefer manual installation:

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install gunicorn
   ```

2. **Configure settings**:
   ```bash
   export DJANGO_SETTINGS_MODULE=mission_tracker.settings_production
   ```

3. **Run migrations**:
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

4. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Django
SECRET_KEY=your-secret-key-here-change-this-in-production
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.mysql
DB_NAME=bossin_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306

# Email (Optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location /static/ {
        alias /var/www/bossin-app/staticfiles/;
        expires 1y;
    }

    location /media/ {
        alias /var/www/bossin-app/media/;
        expires 30d;
    }

    location / {
        proxy_pass http://unix:/var/www/bossin-app/bossin.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Gunicorn Configuration

Create `/etc/systemd/system/bossin-app.service`:

```ini
[Unit]
Description=Bossin Finance Committee App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/bossin-app
ExecStart=/var/www/bossin-app/venv/bin/gunicorn --workers 3 --bind unix:/var/www/bossin-app/bossin.sock mission_tracker.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🔧 Management Commands

### Database Management
```bash
# Create backup
mysqldump -u bossin_user -p bossin_db > backup.sql

# Restore backup
mysql -u bossin_user -p bossin_db < backup.sql
```

### Application Management
```bash
# Restart application
sudo systemctl restart bossin-app

# Check logs
sudo journalctl -u bossin-app -f

# Reload nginx
sudo nginx -t && sudo nginx -s reload
```

## 📊 Monitoring

### Health Checks
- Application: `https://yourdomain.com/health/`
- Database: Check systemd service status
- Logs: `/var/log/django/bossin.log`

### Performance
- Monitor Gunicorn workers
- Check database connections
- Monitor static file serving

## 🔒 Security

- SSL/TLS encryption enabled
- HSTS headers configured
- CSRF protection enabled
- XSS protection active
- Secure session cookies
- File upload restrictions

## 🚀 Scaling

### Horizontal Scaling
- Add more Gunicorn workers
- Use load balancer
- Database read replicas

### Vertical Scaling
- Increase server resources
- Optimize database queries
- Use CDN for static files

## 📞 Support

For support and questions:
- Email: support@kodin.co.tz
- Website: https://kodin.co.tz

## 📝 License

This project is proprietary software developed by Kodin Softwares.

---

**Built with ❤️ by Kodin Softwares**
