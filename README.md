# 🎯 Mission Offering Tracker

A Progressive Web App (PWA) for tracking member contributions, pledges, and progress toward mission goals. Built with Django and Bootstrap 5.

## ✨ Features

### 🔐 Authentication
- Simple login page for committee members ("bosses")
- Session-based access for secure actions
- User-friendly authentication system

### 📊 Dashboard
- **Main Table**: Index | Name | Pledged | Paid | Remaining
- **Statistics Cards**: Total collected, target amount, progress percentage, member counts
- **Search & Filter**: Search by name, filter by status (Complete, Incomplete, Pledged, Not Started)
- **Inline Updates**: Editable fields with AJAX updates
- **Quick Add**: Add new members directly from search results

### 👤 Member Management
- **Member Detail Pages**: Full profile, transaction history, contact info
- **Transaction Tracking**: Add payments with notes and dates
- **Edit Capabilities**: Update member information and transaction notes
- **Status Tracking**: Visual indicators for payment status

### 📈 Admin Log
- **Transaction History**: All payments entered by committee members
- **Filtering**: By admin user, date, or amount
- **Audit Trail**: Track who added what and when
- **Editable Notes**: Update transaction notes inline

### 🎨 User Interface
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Modern UI**: Bootstrap 5 with custom styling
- **Interactive Elements**: Hover effects, loading spinners, success feedback
- **Clean Navigation**: Intuitive menu structure

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Imancharlie/finance-committe-app.git
   cd finance-committe-app
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the database**
   ```bash
   python manage.py migrate
   ```

4. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

5. **Load sample data (optional)**
   ```bash
   python manage.py load_sample_data
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Open http://localhost:8000
   - Login with your superuser credentials

## 📋 Data Models

### Member
- `name` - Full name of the member
- `pledge` - Pledged amount (default: 70,000 TZS)
- `paid_total` - Total amount paid (auto-calculated)
- `phone`, `email`, `course`, `year` - Optional contact/academic info
- `created_at`, `updated_at` - Timestamps

### Transaction
- `member` - Foreign key to Member
- `amount` - Payment amount
- `date` - Payment date
- `added_by` - Admin user who entered the transaction
- `note` - Optional notes about the payment

## 🎯 Core Workflows

### Adding a New Member
1. Go to Dashboard → "Add Member" button
2. Fill in required fields (name, pledge amount)
3. Add optional contact information
4. Member is created with default 70,000 TZS pledge

### Recording a Payment
1. Click on member name from dashboard
2. Scroll to "Add New Payment" section
3. Enter amount, date, and optional notes
4. Payment is recorded and member totals are updated

### Quick Member Addition
1. Search for a member name
2. If not found, "Add New Member" button appears
3. Quick form opens in modal
4. Member is added and search continues

### Tracking Progress
- Dashboard shows overall progress toward target
- Individual member status is color-coded
- Filter by payment status to focus on specific groups

## 🔧 Configuration

### Target Amount
The target amount (currently set to 10,000,000 TZS) can be modified in `tracker/views.py`:
```python
target_amount = 10000000  # Adjust this value
```

### Default Pledge
The default pledge amount (70,000 TZS) can be changed in `tracker/models.py`:
```python
pledge = models.DecimalField(
    max_digits=10, 
    decimal_places=2, 
    default=70000.00,  # Adjust this value
    ...
)
```

## 🛠️ Technical Details

### Technology Stack
- **Backend**: Django 4.2+
- **Frontend**: Bootstrap 5, jQuery
- **Database**: SQLite (default), supports PostgreSQL/MySQL
- **PWA**: Service Worker, Web App Manifest
- **Icons**: Bootstrap Icons

### Key Features
- **AJAX Updates**: Smooth inline editing without page reloads
- **Responsive Design**: Mobile-first approach
- **Form Validation**: Client and server-side validation
- **Security**: CSRF protection, session management
- **Admin Interface**: Django admin for backup control

### File Structure
```
Finance_committee_app/
├── mission_tracker/          # Django project settings
├── tracker/                  # Main application
│   ├── models.py            # Data models
│   ├── views.py             # View logic
│   ├── forms.py             # Form definitions
│   ├── admin.py             # Admin interface
│   └── urls.py              # URL routing
├── templates/               # HTML templates
│   ├── base.html           # Base template
│   └── tracker/            # App-specific templates
├── static/                 # Static files (CSS, JS)
├── manage.py               # Django management script
└── requirements.txt        # Python dependencies
```

## 🚀 Deployment

### Development
```bash
python manage.py runserver
```

### Production Considerations
1. **Database**: Use PostgreSQL or MySQL instead of SQLite
2. **Static Files**: Configure proper static file serving
3. **Security**: Set `DEBUG = False` and configure `ALLOWED_HOSTS`
4. **Web Server**: Use Gunicorn with Nginx
5. **Environment Variables**: Store sensitive settings in environment variables

## 🤝 Contributing

This project is designed for the specific needs of your fellowship finance committee. Feel free to customize and extend it according to your requirements.

## 📞 Support

For questions or issues related to this application, please contact your finance committee or the development team.

---

**Mission**: Supporting the evangelism mission to Mlali Village, Mvomero District, Morogoro  
**Purpose**: Efficiently track and manage member contributions for the mission offering 

## PWA Features

- ✅ **Installable** - Add to home screen on mobile/desktop
- ✅ **Offline Support** - Navigate and view cached pages offline
- ✅ **Background Sync** - Sync data when connection is restored
- ✅ **App-like Experience** - Standalone window mode

## Usage

### Dashboard
- View overall progress and statistics
- Search and filter members
- Quick member addition

### Member Management
- Add new members with contact information
- Track individual payment progress
- View detailed transaction history

### Daily Collection
- Record payments for multiple members
- Quick input interface for daily collections
- Real-time updates

### Admin Log
- View all transactions
- Filter by admin, date, or amount
- Edit transaction notes

### Excel Import
- Import members from Excel files
- Support for bulk member creation
- Update existing members

## Management Commands

```bash
# Load sample data
python manage.py load_sample_data

# Fix member totals (if needed)
python manage.py fix_member_totals

# Clean database (if needed)
python manage.py clean_database
```

## Browser Support

- Chrome 67+
- Firefox 67+
- Safari 11.1+
- Edge 79+

## License

This project is licensed under the MIT License.

## Support

For support or questions, please open an issue on GitHub.

---

**Built with ❤️ for mission finance committees** 