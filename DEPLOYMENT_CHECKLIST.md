# 📋 Deployment Checklist - Dual Authentication System

Use this checklist to track your deployment progress.

---

## Phase 1: Pre-Deployment Setup

### Environment Configuration
- [ ] Copy `.env.example` to `.env`
- [ ] Generate strong `SECRET_KEY` (run: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- [ ] Set `DATABASE_URL` with your PostgreSQL credentials
- [ ] Set `REDIS_URL` for Celery (future use)
- [ ] Set `ENVIRONMENT=development` (or `production`)

### WhatsApp API Setup (Meta Business Suite)
- [ ] Create/Login to Meta Business Account at https://business.facebook.com/
- [ ] Navigate to WhatsApp → API Setup
- [ ] Get **Access Token** → Add to `.env` as `PLATFORM_WHATSAPP_TOKEN`
- [ ] Get **Phone Number ID** → Add to `.env` as `PLATFORM_PHONE_NUMBER_ID`
- [ ] Test phone number is verified in WhatsApp Business
- [ ] Verify phone number has messaging permissions

---

## Phase 2: Database Setup

### Backup Current Database
- [ ] Create backup: `pg_dump -U username -d ektola > backup.sql`
- [ ] Save backup to safe location
- [ ] Verify backup file exists and has content

### Generate Migration
- [ ] Run: `alembic revision --autogenerate -m "Add Admin and OTP models, update Jeweller"`
- [ ] Migration file created in `alembic/versions/`
- [ ] Open migration file and review changes

### Review Migration Content
- [ ] Verify `admins` table creation with all columns
- [ ] Verify `otps` table creation with all columns
- [ ] Verify `jewellers` table modifications:
  - [ ] Removes `user_id` column
  - [ ] Adds `owner_name` column
  - [ ] Adds `email` column (unique)
  - [ ] Adds `is_verified` column
  - [ ] Adds `onboarding_completed` column
  - [ ] Adds `last_login` column

### Apply Migration
- [ ] Run: `alembic upgrade head`
- [ ] No errors in output
- [ ] Verify with: `alembic current`
- [ ] Check tables exist: `psql -d ektola -c "\dt"`

### Verify Database Structure
```bash
# Run these SQL queries to verify:
```
- [ ] `SELECT * FROM admins LIMIT 1;` (table exists)
- [ ] `SELECT * FROM otps LIMIT 1;` (table exists)
- [ ] `\d jewellers` (verify new columns exist)

---

## Phase 3: Create First Admin

### Run Super Admin Script
- [ ] Run: `python create_super_admin.py`
- [ ] Enter admin details:
  - [ ] Valid email address
  - [ ] Strong password (min 8 chars)
  - [ ] Optional phone number
- [ ] Script completes successfully
- [ ] Admin ID displayed

### Verify Admin Creation
- [ ] List admins: `python create_super_admin.py --list`
- [ ] Admin appears in list
- [ ] Role is `super_admin`
- [ ] Status is `Active`

---

## Phase 4: Test Authentication

### Test Admin Login (cURL)
```bash
curl -X POST http://localhost:8000/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your_admin@email.com",
    "password": "your_password"
  }'
```
- [ ] Request returns 200 status
- [ ] Response contains `access_token`
- [ ] Response contains `user_type: "admin"`
- [ ] Token is valid JWT format

### Test Admin Protected Endpoint
```bash
# Replace YOUR_TOKEN with token from previous step
curl -X GET http://localhost:8000/auth/me/admin \
  -H "Authorization: Bearer YOUR_TOKEN"
```
- [ ] Request returns 200 status
- [ ] Response contains admin profile
- [ ] Role and permissions displayed correctly

### Test WhatsApp OTP Request
```bash
curl -X POST http://localhost:8000/auth/jeweller/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919876543210"}'
```
- [ ] Request returns 200 status
- [ ] Response indicates OTP sent
- [ ] Check WhatsApp: OTP message received
- [ ] OTP format is correct (6 digits)

### Test OTP Verification
```bash
curl -X POST http://localhost:8000/auth/jeweller/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+919876543210",
    "otp_code": "123456"
  }'
```
- [ ] Request returns 200 status (with correct OTP)
- [ ] Response contains `access_token`
- [ ] Response contains `user_type: "jeweller"`
- [ ] Token is valid JWT format

### Test Jeweller Protected Endpoint
```bash
curl -X GET http://localhost:8000/auth/me/jeweller \
  -H "Authorization: Bearer YOUR_JEWELLER_TOKEN"
```
- [ ] Request returns 200 status
- [ ] Response contains jeweller profile
- [ ] All fields populated correctly

---

## Phase 5: API Documentation

### Check Swagger UI
- [ ] Visit: http://localhost:8000/docs
- [ ] All auth endpoints visible
- [ ] Jeweller endpoints grouped correctly
- [ ] Admin endpoints grouped correctly
- [ ] Schemas display properly

### Test via Swagger
- [ ] Test admin login via Swagger UI
- [ ] Click "Authorize" and paste token
- [ ] Test protected endpoint works with token
- [ ] Test jeweller OTP flow via Swagger

---

## Phase 6: Frontend Integration (If Applicable)

### Admin Login Page
- [ ] Create admin login form (email + password)
- [ ] Implement POST to `/auth/admin/login`
- [ ] Store token in localStorage/sessionStorage
- [ ] Redirect to admin dashboard on success
- [ ] Display error messages properly

### Jeweller Login Page
- [ ] Create jeweller login form (phone number)
- [ ] Implement POST to `/auth/jeweller/request-otp`
- [ ] Show OTP input field
- [ ] Implement POST to `/auth/jeweller/verify-otp`
- [ ] Store token after verification
- [ ] Redirect to jeweller dashboard

### Protected Routes
- [ ] Add Authorization header to API calls
- [ ] Handle 401 errors (token expired)
- [ ] Handle 403 errors (insufficient permissions)
- [ ] Implement token refresh or re-login

---

## Phase 7: Security Verification

### Token Security
- [ ] Tokens are using secure SECRET_KEY (not default)
- [ ] SECRET_KEY is not in git repository
- [ ] Admin tokens expire in 8 hours
- [ ] Jeweller tokens expire in 30 days
- [ ] Token validation works on all protected endpoints

### OTP Security
- [ ] OTP expires after 10 minutes
- [ ] Max 3 attempts enforced
- [ ] OTP is single-use (marked verified after use)
- [ ] Previous OTPs invalidated on new request
- [ ] OTP messages clearly state expiry time

### Password Security
- [ ] Passwords hashed with bcrypt
- [ ] Minimum 8 character requirement enforced
- [ ] Passwords never logged or displayed
- [ ] Failed login attempts don't reveal if user exists

### API Security
- [ ] CORS configured properly for your domain
- [ ] HTTPS enabled in production (nginx/load balancer)
- [ ] Rate limiting considered (future enhancement)
- [ ] SQL injection prevented (using SQLAlchemy ORM)

---

## Phase 8: Production Deployment

### Pre-Production
- [ ] All tests passing
- [ ] No errors in logs
- [ ] Database migrations tested
- [ ] Backup strategy in place
- [ ] Rollback plan documented

### Production Checklist
- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Use production database credentials
- [ ] Enable HTTPS (configure reverse proxy)
- [ ] Update CORS to specific origins (not `*`)
- [ ] Set secure headers (HSTS, CSP, etc.)
- [ ] Configure logging to file
- [ ] Set up monitoring (Sentry, DataDog, etc.)
- [ ] Document admin credentials securely

### Post-Deployment
- [ ] Verify admin login works in production
- [ ] Verify jeweller OTP flow works
- [ ] Monitor logs for errors
- [ ] Test from actual mobile device (jeweller flow)
- [ ] Verify WhatsApp messages received
- [ ] Test rate limiting if implemented

---

## Phase 9: Future Enhancements

### Short-term (Next Sprint)
- [ ] Create admin dashboard UI
- [ ] Implement jeweller approval workflow
- [ ] Add jeweller management endpoints for admins
- [ ] Implement campaign execution with Celery
- [ ] Add message sending background jobs

### Medium-term (Next Month)
- [ ] Add password reset for admins
- [ ] Add phone number change for jewellers
- [ ] Implement session management
- [ ] Add audit logging for admin actions
- [ ] Create analytics dashboard

### Long-term (Next Quarter)
- [ ] Add 2FA for super admins
- [ ] Implement API rate limiting
- [ ] Add admin activity logs
- [ ] Create jeweller onboarding flow
- [ ] Multi-language support for OTP messages

---

## Rollback Plan (If Needed)

### If Migration Fails
1. [ ] Stop application server
2. [ ] Restore database: `psql -U username -d ektola < backup.sql`
3. [ ] Rollback Alembic: `alembic downgrade -1`
4. [ ] Investigate error logs
5. [ ] Fix migration script
6. [ ] Retry

### If WhatsApp Not Working
1. [ ] Verify credentials in `.env`
2. [ ] Check Meta Business Suite for errors
3. [ ] Test with Postman directly to WhatsApp API
4. [ ] Verify phone number permissions
5. [ ] Check rate limits not exceeded

### If Authentication Broken
1. [ ] Restore previous code from git
2. [ ] Rollback database to backup
3. [ ] Review error logs
4. [ ] Test in development first
5. [ ] Redeploy when fixed

---

## 📞 Support Resources

### Documentation
- **Implementation Guide:** [AUTHENTICATION_IMPLEMENTATION.md](AUTHENTICATION_IMPLEMENTATION.md)
- **Migration Guide:** [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **Quick Reference:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Summary:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

### External Help
- **Meta WhatsApp:** https://developers.facebook.com/docs/whatsapp/
- **FastAPI Security:** https://fastapi.tiangolo.com/tutorial/security/
- **Alembic Docs:** https://alembic.sqlalchemy.org/

---

## ✅ Completion Sign-off

### Development Environment
- [ ] All checklist items completed
- [ ] Tests passing
- [ ] Documentation reviewed
- **Deployed by:** ________________
- **Date:** ________________

### Production Environment
- [ ] All checklist items completed
- [ ] Production tests passing
- [ ] Monitoring active
- **Deployed by:** ________________
- **Date:** ________________
- **Verified by:** ________________

---

**Status Legend:**
- [ ] Not Started
- [⏳] In Progress
- [✅] Completed
- [❌] Blocked/Issue

**Last Updated:** February 1, 2026
