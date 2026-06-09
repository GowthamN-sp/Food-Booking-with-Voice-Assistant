# EchoEats - Voice Assistant Django Backend

A sophisticated Django REST API for the EchoEats voice-controlled food ordering application with Groq AI integration and Razorpay payment processing.

## 🔐 Security Features

✅ **Secrets Management**: All sensitive credentials are stored in `.env` files (not tracked by Git)
✅ **Environment Variables**: Industry-standard configuration management using `python-dotenv`
✅ **API Keys Secured**: Groq, Razorpay credentials completely removed from source code
✅ **Database Credentials**: MySQL credentials loaded from environment
✅ **Production Ready**: Proper security headers and configuration best practices

## 📋 Prerequisites

- Python 3.8+
- MySQL 5.7+
- pip (Python package manager)
- Git

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ECHO_EATS_VOICE_ASSISTANT_DJANGO.git
cd FoodApp/Backend
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

**CRITICAL: This step must be completed before running the application**

```bash
# Copy the example environment file
cp .env.example .env
```

**Edit `.env` and add your actual credentials:**

```env
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=voiceassistant
DB_USER=root
DB_PASSWORD=your-database-password
DB_HOST=localhost
DB_PORT=3306

# Groq API (Voice AI)
GROQ_API_KEY=your-groq-api-key

# Razorpay Payment
RAZORPAY_KEY_ID=your-razorpay-key-id
RAZORPAY_KEY_SECRET=your-razorpay-secret-key

# CORS Settings
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 5. Run Database Migrations

```bash
python manage.py migrate
```

### 6. Start Development Server

```bash
python manage.py runserver 8000
```

The API will be available at: `http://localhost:8000`

## 📖 API Endpoints

### Food Items
- `GET /api/food-items` - Get all food items
- `POST /api/update-quantity/<id>/` - Update item quantity

### Voice Processing
- `POST /api/process-voice/` - Process voice commands

### User Management
- `POST /api/login/` - User login
- `POST /api/signup/` - User registration
- `POST /api/logout/<user_id>/` - User logout

### Orders
- `POST /api/create-order/` - Create new order
- `POST /api/verify-payment/` - Verify payment
- `GET /api/user-orders/<user_id>/` - Get user orders
- `POST /api/update-order-status/<order_id>/` - Update order status

### Cart
- `POST /api/session-cart/` - Update session cart
- `GET /api/session-cart/<session_id>/` - Get session cart items
- `DELETE /api/session-cart/<session_id>/` - Clear session cart

## 🔑 Getting API Keys

### Groq API Key
1. Visit: https://console.groq.com
2. Sign up or log in
3. Create an API key
4. Copy and paste into `.env`

### Razorpay Keys
1. Visit: https://dashboard.razorpay.com
2. Go to Settings → API Keys
3. Copy Key ID and Key Secret
4. Add to `.env`

## 🏗️ Project Structure

```
Backend/
├── Backend/
│   ├── settings.py          # Django settings (uses environment variables)
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI configuration
├── app/
│   ├── models.py            # Database models
│   ├── views.py             # API views
│   ├── urls.py              # App-specific URLs
│   └── migrations/          # Database migrations
├── manage.py                # Django management
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## 🔒 Security Best Practices

### Never Commit `.env`
The `.env` file contains sensitive credentials and is protected by `.gitignore`. **Never** commit this file to version control.

```bash
# Verify .env is not tracked:
git status
# Should NOT show .env in changes
```

### Environment Variables Used
- `DJANGO_SECRET_KEY` - Django's secret key for cryptographic signing
- `DEBUG` - Set to `False` in production
- `DB_PASSWORD` - Database password
- `GROQ_API_KEY` - Groq AI API key
- `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` - Payment gateway credentials

### Production Deployment
For production:

```env
DEBUG=False
DJANGO_SECRET_KEY=generate-with-django-secret-key-generator
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific test
python manage.py test app.tests.YourTestCase

# With coverage
coverage run --source='.' manage.py test
coverage report
```

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 6.0.4 | Web framework |
| djangorestframework | 3.14.0 | REST API |
| django-cors-headers | 4.3.1 | CORS support |
| mysqlclient | 2.2.1 | MySQL driver |
| groq | 0.4.2 | Groq AI API |
| razorpay | 1.4.1 | Payment processing |
| python-dotenv | 1.2.2 | Environment variables |
| openai | 1.3.0 | OpenAI/Groq compatibility |

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'dotenv'"
```bash
pip install python-dotenv
```

### "No module named 'groq'"
```bash
pip install groq
```

### Database Connection Error
- Verify MySQL is running
- Check DB credentials in `.env`
- Ensure database exists: `CREATE DATABASE voiceassistant;`

### CORS Errors
- Verify `CORS_ALLOWED_ORIGINS` in `.env` includes your frontend URL
- Frontend should be running on `http://localhost:3000` or `http://localhost:5173`

### Groq API Key Error
- Verify `GROQ_API_KEY` is correctly set in `.env`
- Ensure the key is valid at: https://console.groq.com

## 🚢 Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### Environment Variables on Deployment
Set environment variables through your hosting platform:
- Heroku: Use Config Vars
- AWS: Use Parameter Store or Secrets Manager
- Azure: Use Key Vault
- DigitalOcean: Use App Platform Environment Variables

## 📝 Git Workflow

After making changes:

```bash
# Check status
git status

# Verify .env is NOT listed
# If .env appears, it means .gitignore is not working properly

# Add changes
git add .

# Commit
git commit -m "Fix: Remove hardcoded secrets and implement environment variables"

# Push
git push origin main
```

## 🔄 Migration Guide

If you're migrating from hardcoded secrets:

1. ✅ Update all settings files to use `os.getenv()`
2. ✅ Create `.env.example` with placeholder values
3. ✅ Add `.env` to `.gitignore`
4. ✅ Update all developers to copy `.env.example` to `.env`
5. ✅ Remove all hardcoded credentials from Git history (see below)

### Remove Secrets from Git History
If secrets were already committed:

```bash
# Warning: This rewrites history for all users
# Option 1: Using git-filter-repo (recommended)
pip install git-filter-repo
git filter-repo --invert-paths --paths .env

# Option 2: Force push (nuclear option)
git push --force-with-lease
```

**After removing secrets from history:**
- All team members must refetch: `git fetch --all && git reset --hard`
- Regenerate all compromised API keys
- Notify your security team

## 📚 Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Groq API Docs](https://console.groq.com/docs)
- [Razorpay Integration](https://razorpay.com/docs/)
- [python-dotenv](https://python-dotenv.readthedocs.io/)
- [12-Factor App - Config](https://12factor.net/config)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes
4. Commit: `git commit -m "Add amazing feature"`
5. Push: `git push origin feature/amazing-feature`
6. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## ⚠️ Security Notice

**DO NOT:**
- Commit `.env` files
- Hardcode API keys in source code
- Share credentials in pull requests or issues
- Use test credentials in production

**DO:**
- Use environment variables for all secrets
- Rotate API keys regularly
- Review `.gitignore` before committing
- Report security issues privately

## 📞 Support

For issues and questions:
- GitHub Issues: [Report a bug](https://github.com/yourusername/ECHO_EATS_VOICE_ASSISTANT_DJANGO/issues)
- Email: support@echorats.com

---

**Last Updated**: 2026-06-09
**Status**: ✅ Production Ready | 🔐 GitHub Safe | 🛡️ Security Verified
