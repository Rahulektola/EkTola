# Authentication Quick Reference

## 🚀 Quick Start

### 1. Database Setup
```bash
# Make sure PostgreSQL is running
# Configure DATABASE_URL in .env or config.py

# Run migrations
alembic upgrade head
```

### 2. Create First Admin
```bash
# Using API endpoint
curl -X POST http://localhost:8000/auth/admin/create-first-admin \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Platform Admin",
    "email": "admin@ektola.com",
    "password": "SecurePass123!",
    "phone_number": "+919876543210"
  }'
```

### 3. Configure WhatsApp
```bash
# In .env file
PLATFORM_WHATSAPP_TOKEN=EAAxxxxxxxxxxxxx
PLATFORM_PHONE_NUMBER_ID=123456789012345
```

## 📱 Jeweller Flow

### Signup
```bash
# Step 1: Request OTP
curl -X POST http://localhost:8000/auth/jeweller/signup/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919876543210"}'

# Step 2: Verify OTP and Register
curl -X POST http://localhost:8000/auth/jeweller/signup/verify-and-register \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+919876543210",
    "otp_code": "123456",
    "business_name": "Golden Jewellers",
    "owner_name": "John Doe",
    "email": "john@goldenjewellers.com",
    "whatsapp_business_account_id": "your_waba_id",
    "whatsapp_phone_number_id": "your_phone_id"
  }'

# Response includes JWT token
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user_type": "jeweller",
  "user_data": {
    "id": 1,
    "business_name": "Golden Jewellers",
    "is_approved": false,
    "is_active": false
  }
}
```

### Login
```bash
# Step 1: Request OTP
curl -X POST http://localhost:8000/auth/jeweller/login/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919876543210"}'

# Step 2: Verify OTP
curl -X POST http://localhost:8000/auth/jeweller/login/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+919876543210",
    "otp_code": "123456"
  }'
```

## 👨‍💼 Admin Flow

### Login
```bash
curl -X POST http://localhost:8000/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@ektola.com",
    "password": "SecurePass123!"
  }'

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user_type": "admin",
  "user_data": {
    "id": 1,
    "full_name": "Platform Admin",
    "email": "admin@ektola.com"
  }
}
```

### Approve Jeweller
```bash
# Get pending jewellers
curl -X GET http://localhost:8000/admin/jewellers/pending \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Approve specific jeweller
curl -X POST http://localhost:8000/admin/jewellers/1/approve \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Create Another Admin
```bash
curl -X POST http://localhost:8000/admin/admins/create \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Support Admin",
    "email": "support@ektola.com",
    "password": "AnotherSecurePass123!",
    "phone_number": "+919876543211"
  }'
```

## 🔐 Using JWT Tokens

### With cURL
```bash
curl -X GET http://localhost:8000/contacts \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### With JavaScript (Frontend)
```javascript
// Store token after login
localStorage.setItem('token', response.access_token);

// Use in API calls
fetch('http://localhost:8000/contacts', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
})
```

### With Python (requests)
```python
import requests

headers = {
    'Authorization': f'Bearer {token}'
}

response = requests.get('http://localhost:8000/contacts', headers=headers)
```

## ⚙️ Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ektola

# JWT
SECRET_KEY=your-secret-key-min-32-chars-long
ALGORITHM=HS256

# WhatsApp (Platform credentials for sending OTPs)
PLATFORM_WHATSAPP_TOKEN=EAAxxxxxxxxxxxxx
PLATFORM_PHONE_NUMBER_ID=123456789012345

# Environment
ENVIRONMENT=development
```

## 🔍 Check API Documentation

Once the server is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## 🐛 Troubleshooting

### OTP Not Received
```python
# Check WhatsApp service configuration
# Verify PLATFORM_WHATSAPP_TOKEN and PLATFORM_PHONE_NUMBER_ID
# Check logs for API errors
```

### Token Expired
```python
# Jeweller: Token valid for 30 days
# Admin: Token valid for 8 hours
# Re-login to get new token
```

### Database Connection Failed
```bash
# Check PostgreSQL is running
pg_ctl -D /path/to/data status

# Test connection
psql -U user -d ektola -h localhost
```

### Jeweller Can't Access Features
```python
# Check if jeweller is approved
GET /auth/me/jeweller

# Admin must approve jeweller
POST /admin/jewellers/{id}/approve
```

## 📊 User States

### Jeweller States
| State | is_verified | is_approved | is_active | subscription_status | Can Login? | Can Use Features? |
|-------|-------------|-------------|-----------|---------------------|------------|-------------------|
| New Signup | ✅ | ❌ | ❌ | trial | ✅ | ❌ |
| Approved | ✅ | ✅ | ✅ | trial | ✅ | ✅ |
| Active Paid | ✅ | ✅ | ✅ | active | ✅ | ✅ |
| Suspended | ✅ | ✅ | ❌ | suspended | ✅ | ❌ |

### Admin States
| State | is_active | Can Login? | Can Manage? |
|-------|-----------|------------|-------------|
| Active | ✅ | ✅ | ✅ |
| Deactivated | ❌ | ❌ | ❌ |

## 🎯 Common Workflows

### New Jeweller Onboarding
1. Jeweller signs up with phone number (OTP verification)
2. Jeweller account created (status: not approved, not active)
3. Admin reviews pending jewellers
4. Admin approves jeweller
5. Jeweller becomes active (subscription_status: trial)
6. Jeweller can now use all features

### Subscription Management
```bash
# Deactivate jeweller (non-payment)
POST /admin/jewellers/{id}/deactivate

# Reactivate jeweller (payment received)
POST /admin/jewellers/{id}/activate
```

### Admin Team Management
```bash
# Current admin creates new admin
POST /admin/admins/create

# View all admins
GET /admin/admins/all

# Deactivate admin (if needed, direct DB update required)
# UPDATE admins SET is_active = false WHERE id = X
```

## 📝 Response Schemas

### Token Response
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_type": "jeweller" | "admin",
  "user_data": {
    // User-specific fields
  }
}
```

### Error Response
```json
{
  "detail": "Error message here"
}
```

## 🚨 Security Best Practices

1. **Never commit tokens or secrets to Git**
2. **Use environment variables for sensitive data**
3. **Rotate JWT secret keys periodically**
4. **Use HTTPS in production**
5. **Implement rate limiting for OTP endpoints**
6. **Monitor failed login attempts**
7. **Keep WhatsApp tokens secure**

## 📞 Support

For issues or questions:
- Check logs: `tail -f app.log`
- Check database: `psql -U user -d ektola`
- Review API docs: http://localhost:8000/docs
