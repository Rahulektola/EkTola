=# EkTola Project Audit — April 12, 2026 (Revised)

## Current Goal

**Complete Meta App Review** by sending live SIP/Loan payment reminder messages. This requires advanced access permissions (business_management). The MVP flow is:

1. Admin creates & manages WhatsApp message templates (provided to jewellers)
2. Jeweller registers → admin approves → jeweller connects WhatsApp via Embedded Signup
3. Jeweller adds contacts → selects segment (SIP / Loan / Both) → sets payment day & reminder days
4. System auto-sends WhatsApp reminders daily via Celery Beat
5. Webhooks track delivery status

**Campaign creation/management is a planned future feature — not part of the current MVP.**

---

## Overall Completion: ~75% (for MVP reminder flow)

The reminder pipeline (contacts → schedule → auto-send) is substantially complete end-to-end. Auth, contacts, admin panel, and WhatsApp onboarding are all working. The remaining work is fixing a few bugs, hardening for production, and deploying.

---

## BUGS BLOCKING MVP (must fix before first live message)

| # | Bug | File | Impact | Effort |
|---|-----|------|--------|--------|
| 1 | `webhook.py` has `processed = Column(String, default=False)` | `app/models/webhook.py` | Stores `"False"` string instead of boolean — webhook delivery tracking broken | 10 min |
| 2 | `template_service.py` `update_message_status()` is truncated — no timestamp updates, no `db.commit()` | `app/services/template_service.py` | **Delivery/read status never persisted** — Meta won't see proper status handling | 1 hr |

---

## PRODUCTION HARDENING (must fix before deployment)

| # | Issue | File | Effort |
|---|-------|------|--------|
| 1 | `allow_origins=["*"]` — must restrict to actual frontend domain | `app/main.py` | 10 min |
| 2 | Dev mode leaks OTP in API response — must disable for production | `app/services/auth_routes.py` | 10 min |
| 3 | Webhook signature verification skipped when app secret not set | `app/services/webhook_routes.py` | 10 min |
| 4 | Webhook verify token accepts anything when platform token not set | `app/services/webhook_routes.py` | 10 min |
| 5 | No Alembic migrations — schema changes can't be applied safely | Project-wide | 2-3 hrs |
| 6 | No deployment infrastructure (Dockerfile, docker-compose, nginx) | Project-wide | Half a day |
| 7 | No rate limiting on WhatsApp sends | `app/services/whatsapp_service.py` | 2-3 hrs |

---

## META APP REVIEW REQUIREMENTS

To pass Meta's app review and gain advanced access:

| Requirement | Status |
|-------------|--------|
| Approved WhatsApp message templates (SIP + Loan reminders) | **Must create in Meta Business Manager** |
| `WHATSAPP_SIP_REMINDER_TEMPLATE` + `WHATSAPP_LOAN_REMINDER_TEMPLATE` configured in `.env` | **Must match approved template names** |
| Live webhook endpoint receiving delivery status updates | **Backend ready** (once bug #1-2 above fixed) |
| Proper webhook signature verification (HMAC) | **Code exists** — must ensure `WHATSAPP_APP_SECRET` is set |
| Privacy policy URL | **Completed** |
| Business verification | **Completed** |

---

## CAMPAIGN FEATURES (Future — NOT part of current MVP)

The following are **planned for later phases** and are not blocking the current goal. Known bugs in campaign code are documented here for future reference only.

| Item | Status | Known Issues |
|------|--------|-------------|
| `campaigns.html` frontend page | **Not built** — planned | No frontend coverage for 10 backend endpoints |
| `templates.html` frontend page | **Not built** — planned | No frontend coverage for 11 backend endpoints (admin manages templates directly for now) |
| `campaign_tasks.py` references `message.campaign_id` | **Bug** — `Message` model only has `campaign_run_id` | Will crash when campaigns are enabled |
| `campaign_routes.py` uses undefined `stats` variable | **Bug** — should be `result` | Stats endpoint will crash |
| `campaign_tasks.py` uses `asyncio.run()` per message | **Performance** — creates/destroys event loop per message | Won't scale for campaigns |
| Direct message send UI | **Not built** — planned | |
| Profile page | **Stub only** — `alert('coming soon')` | |

---

## WHAT'S WORKING WELL (Complete for MVP)

### Reminder Pipeline (Core MVP)
- **`reminder_tasks.py`** — Excellent design. `ReminderConfig` dataclass handles both SIP and Loan. Month-end edge cases covered. Deduplication (won't re-send same month). Runs daily at 9 AM IST via Celery Beat.
- **`whatsapp_service.py`** — Dual-mode: PyWa async for platform OTP, sync HTTPX for per-jeweller sends. Dev mode returns fake success for testing.
- **`webhook_routes.py`** — Handles delivery status updates (sent/delivered/read/failed). Multi-tenant routing by `phone_number_id`.
- **`token_refresh.py`** — Auto-refreshes expiring WABA tokens (7-day window). Checks for expired tokens.

### Auth & User Management
- **Auth system** — Phone/email login, JWT tokens, admin auth
- **WhatsApp Embedded Signup** — Full 8-step OAuth flow to onboard jewellers (might change once we actually figure out coexistence)
- **Token encryption** — Fernet encryption for WABA tokens at rest

### Contact Management (Frontend + Backend)
- **Full CRUD** — Add, edit, delete, search, filter, pagination
- **Bulk operations** — Upload CSV, bulk edit segment, bulk delete
- **Payment scheduling UI** — Jeweller sets `sip_payment_day`, `loan_payment_day`, reminder days via edit modal
- **Segment management** — SIP/Loan/Both with automatic merge handling on duplicate phones

### Admin Panel (Frontend + Backend)
- **Jeweller management** — List, approve/reject, view details, impersonate
- **Analytics** — Dashboard KPIs, detailed breakdowns
- **Contact diagnostics** — Admin can view/upload contacts for any jeweller
- **Deleted contacts** — Restore/purge functionality

### Infrastructure
- **Celery Beat** — Scheduled tasks for reminders, campaign checks, token refresh
- **`DatabaseTask` base class** — Clean session-per-task with cleanup, prevents leaks
- **Batch aggregation** — Admin routes use batch queries to avoid N+1 (Jeweller Route is fixed)

---

## BACKEND FILE-BY-FILE ANALYSIS

### Infrastructure

| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `app/main.py` | FastAPI entry point | **Complete** | CORS needs locking down for production |
| `app/config.py` | Settings via pydantic-settings | **Complete** | WhatsApp settings default to `""` — production needs validation |
| `app/database.py` | SQLAlchemy engine + session | **Complete** | Sync engine (works but not optimal with async endpoints) |
| `app/celery_app.py` | Celery config + beat schedule | **Complete** | Beat covers reminders (daily 9 AM IST), token refresh, campaign checks |
| `requirements.txt` | Dependencies | **Complete** | `alembic` listed but not initialized |

### Models

| File | Purpose | Status |
|------|---------|--------|
| `app/models/user.py` | Auth user | **Complete** |
| `app/models/jeweller.py` | Multi-tenant jeweller | **Complete** — all WhatsApp fields present |
| `app/models/contact.py` | Customer contacts | **Complete** — payment scheduling fields, check constraints, composite indexes |
| `app/models/campaign.py` | Campaigns + runs | **Complete** (future feature) |
| `app/models/message.py` | Message tracking | **Complete for reminders** — `campaign_id` bug only affects campaigns (future) |
| `app/models/template.py` | Template + translations | **Complete** — multi-language support |
| `app/models/webhook.py` | Webhook event log | **BUG** — `processed` column is `String`, should be `Boolean` |

### Core

| File | Purpose | Status |
|------|---------|--------|
| `app/core/security.py` | JWT + bcrypt | **Complete** |
| `app/core/encryption.py` | Fernet token encryption | **Complete** — clean implementation |
| `app/core/dependencies.py` | FastAPI auth dependencies | **Complete** — checks `is_approved` and `is_active` |
| `app/core/datetime_utils.py` | UTC datetime helpers | **Complete** |
| `app/utils/enums.py` | All enums | **Complete** |

### Services — MVP Core

| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `app/services/whatsapp_service.py` | Messaging engine | **Mostly complete** | Sync HTTPX for per-jeweller sends works. Dev mode fakes success. |
| `app/services/whatsapp_auth_routes.py` | Embedded Signup OAuth | **Complete** | Full flow: code exchange → long-lived token → WABA discovery → encrypt & store → subscribe webhooks |
| `app/services/webhook_routes.py` | Webhook receiver | **Mostly complete** | Status updates work. TODO: incoming message handling (not needed for MVP). |
| `app/services/token_refresh.py` | Token refresh tasks | **Complete** | TODO: Admin notification for failures (nice-to-have). |
| `app/services/reminder_tasks.py` | SIP/Loan reminders | **Complete** | The core MVP task. Well-designed, handles edge cases. |
| `app/services/template_service.py` | Template rendering + messaging | **BUG** | `update_message_status` truncated — must fix for webhook status tracking. |

### Services — Supporting

| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `app/services/contact_routes.py` | Contact CRUD + bulk upload | **Complete** | Payment schedule endpoints included |
| `app/services/auth_routes.py` | Authentication | **Complete** | Dev mode OTP leak must be disabled for production |
| `app/services/admin_routes.py` | Admin panel | **Complete** | Batch aggregates, approval workflow |
| `app/services/analytics_routes.py` | Dashboard analytics | **Complete** | Raw SQL for admin cross-jeweller queries |
| `app/services/template_routes.py` | Template CRUD + WhatsApp sync | **Complete** | Admin-only write, jeweller read-only |
| `app/services/base_task.py` | Celery database task base | **Complete** | Session cleanup pattern |

### Services — Future (Campaign)

| File | Purpose | Status |
|------|---------|--------|
| `app/services/campaign_routes.py` | Campaign CRUD | **Has known bugs** — `stats` variable, deferred to campaign phase |
| `app/services/campaign_tasks.py` | Campaign execution | **Has known bugs** — `campaign_id`, `asyncio.run()`, deferred to campaign phase |

---

## FRONTEND FILE-BY-FILE ANALYSIS

### HTML Pages

| File | Status | Notes |
|------|--------|-------|
| `frontend/index.html` | **Complete** | Login with password + OTP tabs |
| `frontend/register.html` | **Complete** | Jeweller registration with "pending admin approval" notice |
| `frontend/dashboard.html` | **Functional for MVP** | Stats, WhatsApp connection, contact upload all work. Nav links to campaigns/templates go nowhere (future feature). |
| `frontend/contacts.html` | **Complete** | Full CRUD, bulk ops, payment schedule edit — **this is the jeweller's main MVP interface** |
| `frontend/admin-login.html` | **Complete** | |
| `frontend/admin-register.html` | **Complete** | |
| `frontend/admin/dashboard.html` | **Complete** | 6 KPI cards, jeweller performance table |
| `frontend/admin/jewellers.html` | **Complete** | Status filter tabs, search, pagination |
| `frontend/admin/jeweller-detail.html` | **Complete** | Profile, approval, contacts/campaigns/messages tabs |
| `frontend/admin/analytics.html` | **Complete** | Time-period selector, detailed breakdowns |
| `frontend/admin/deleted-contacts.html` | **Complete** | **Not in Vite build config** — must add |
| `frontend/offline.html` | **Complete** | |

### TypeScript Source Files

| File | Status |
|------|--------|
| `frontend/src/config/api.ts` | **Complete** |
| `frontend/src/services/auth.ts` | **Complete** |
| `frontend/src/pages/login.ts` | **Complete** |
| `frontend/src/pages/register.ts` | **Complete** |
| `frontend/src/pages/admin-login.ts` | **Complete** |
| `frontend/src/pages/admin-register.ts` | **Complete** |
| `frontend/src/pages/dashboard.ts` | **Functional** — two stubs (admin permission, profile) are cosmetic |
| `frontend/src/pages/contacts.ts` | **Complete** — includes payment schedule fields |
| `frontend/src/pages/whatsapp-connect.ts` | **Complete** |
| `frontend/src/admin/common.ts` | **Complete** |
| `frontend/src/admin/dashboard.ts` | **Complete** |
| `frontend/src/admin/analytics.ts` | **Complete** |
| `frontend/src/admin/jeweller-list.ts` | **Complete** |
| `frontend/src/admin/jeweller-detail.ts` | **Complete** |
| `frontend/src/admin/deleted-contacts.ts` | **Complete** |

### Build & Config Issues

| Issue | Impact | Effort |
|-------|--------|--------|
| `admin/deleted-contacts.html` missing from `vite.config.ts` rollup inputs | Page won't be in production build | 5 min |
| Service worker pre-caches `/js/*.js` but Vite outputs to `/assets/*.js` | Broken PWA install | 1 hr |
| `dashboard.html` inline script unregisters all service workers | Actively breaks PWA | 10 min |
| Manifest shortcut references nonexistent `/campaigns/new.html` | Broken PWA shortcut | 5 min (remove or update) |
| Dashboard + Contacts have ~600 lines of inline `<style>` each | Maintenance issue (not blocking) | |

---

## BACKEND API COVERAGE FROM FRONTEND

### Fully Covered (MVP)

- **Auth** (`/auth`) — all endpoints
- **WhatsApp Auth** (`/auth/whatsapp`) — config, callback, disconnect
- **Contacts** (`/contacts`) — CRUD, stats, bulk operations, add-one
- **Admin** (`/admin`) — jewellers CRUD, approve/reject, contacts, diagnostics
- **Analytics** (`/analytics`) — jeweller and admin dashboards

### Not Called From Frontend (but backend works)

These payment schedule endpoints are functional but the contacts page handles scheduling through the main `PATCH /contacts/{id}` endpoint instead:

- `PUT /contacts/{id}/payment-schedule`
- `DELETE /contacts/{id}/payment-schedule`
- `POST /contacts/bulk-payment-schedule`
- `GET /contacts/payment-schedules`
- `GET /contacts/reminder-preview`

### Future Feature (No frontend yet — by design)

| Route Group | Count | Phase |
|-------------|-------|-------|
| Campaigns (`/campaigns`) | 10 endpoints | Future |
| Templates (`/templates`) | 11 endpoints | Future (admin manages directly for now) |

---

## END-TO-END REMINDER FLOW STATUS

```
Jeweller registers            → ✅ Complete (frontend + backend)
Admin approves jeweller       → ✅ Complete (frontend + backend)
Jeweller connects WhatsApp    → ✅ Complete (Embedded Signup OAuth)
Jeweller adds contacts        → ✅ Complete (frontend + backend)
Sets segment (SIP/Loan/Both)  → ✅ Complete (contacts page)
Sets payment day + reminder   → ✅ Complete (edit modal in contacts page)
Celery Beat fires daily 9AM   → ✅ Complete (celery_app.py)
Finds contacts due today      → ✅ Complete (reminder_tasks.py)
Decrypts WABA token           → ✅ Complete (encryption.py)
Sends WhatsApp template msg   → ✅ Complete (whatsapp_service.py)
Creates Message record        → ✅ Complete (reminder_tasks.py)
Webhook receives status       → ⚠️ BUG: processed column type wrong
Persists delivery/read status → ❌ BUG: update_message_status() truncated
```

**The pipeline is 90% complete. Two bugs remain.**

---

## TODOS & STUBS IN CODEBASE

### Relevant to MVP

| Location | Issue | Priority |
|----------|-------|----------|
| `app/services/template_service.py` | `update_message_status` body incomplete | **Must fix** |
| `app/services/token_refresh.py` | `# TODO: Send admin notification about failures` | Nice-to-have |
| `app/services/token_refresh.py` | `# TODO: Send admin notification about expired tokens` | Nice-to-have |

### Future / Low Priority

| Location | Issue |
|----------|-------|
| `app/services/webhook_routes.py` | `# TODO: Handle incoming messages if needed` |
| `app/services/auth_routes.py` | `# TODO: Send OTP via email service` — email OTP just stores code |
| `frontend/src/pages/dashboard.ts` | `alert('Admin permission feature coming soon!')` |
| `frontend/src/pages/dashboard.ts` | `alert('Profile page coming soon!')` |

---

## SECURITY OBSERVATIONS

| Issue | Severity | Action Needed |
|-------|----------|---------------|
| `allow_origins=["*"]` in CORS | Medium | **Must fix for production** — restrict to frontend domain |
| OTP leaked in dev response | Medium | **Must disable for production** — check `DEV_MODE` flag |
| Webhook signature skip when no app secret | Medium | **Must set `WHATSAPP_APP_SECRET`** in production .env |
| Webhook verify accepts any token without config | Medium | **Must set `WHATSAPP_PLATFORM_TOKEN`** in production .env |
| No password complexity validation | Low | Nice-to-have |

---

## DOCUMENTATION GAPS

| Issue | Details |
|-------|---------|
| Root README is self-declared outdated | Line 1: `# OUTDATED DO NOT REFER THIS FILE` |
| Project structure mismatch | README documents `routers/`, `tasks/` dirs that don't exist |
| Database confusion | Root README says PostgreSQL, but project uses MySQL (`pymysql`) |
| 4 documented scripts don't exist | `reset_admin_password.py`, `migrate_admin_dashboard.py`, `migrate_phone_auth.py`, `migrate_whatsapp_signup.py` |
| Frontend README endpoint mismatch | Documents `/auth/request-otp` but backend uses `/auth/otp/request/phone` |
| Quick Start references missing file | `IMPLEMENTATION_SUMMARY.md` doesn't exist |

---

## MINIMUM PATH TO FIRST LIVE REMINDER MESSAGE

### Step 1: Fix 2 Bugs (~1.5 hrs)
- Fix `webhook.py` `processed` → `Boolean`
- Complete `update_message_status()` in `template_service.py`

### Step 2: Production Security (~30 min)
- Lock down CORS origins
- Disable dev-mode OTP leak
- Ensure webhook signature verification is enforced

### Step 3: Meta Business Setup (external)
- Create SIP + Loan reminder templates in Meta Business Manager
- Submit for Meta approval
- Set `WHATSAPP_SIP_REMINDER_TEMPLATE` and `WHATSAPP_LOAN_REMINDER_TEMPLATE` in `.env`
- Complete business verification
- Provide privacy policy URL

### Step 4: Deploy (~half a day)
- Create Dockerfile (FastAPI + Celery worker + Celery Beat)
- Create docker-compose.yml (app + MySQL + Redis)
- Add nginx/Caddy reverse proxy with HTTPS
- Initialize Alembic for future schema changes
- Configure production `.env` with real WABA credentials

### Step 5: Build Config Fixes (~20 min)
- Add `admin/deleted-contacts.html` to Vite build
- Fix or remove broken manifest shortcut
- Fix service worker paths (or disable PWA for now)

---

## FUTURE ROADMAP (after Meta approval)

| Phase | Feature | Status |
|-------|---------|--------|
| **Phase 2** | Campaign creation & management (frontend + fix backend bugs) | Backend ~70% done, frontend 0% |
| **Phase 2** | Template management UI for admin | Backend complete, frontend 0% |
| **Phase 3** | Direct message send UI | Not started |
| **Phase 3** | Payment schedule management dedicated UI | Backend complete, frontend partial |
| **Phase 3** | Email OTP delivery | Backend stub exists |
| **Phase 4** | Profile page | Stub only |
| **Phase 4** | Admin notifications for token failures | TODO in code |
| **Phase 4** | Test suite | Nothing exists |
| **Phase 4** | Incoming message handling | TODO in webhook code |

---

## ARCHITECTURAL NOTES

**Good patterns:**
- Multi-tenant isolation via `jeweller_id` FK on all data
- Token encryption at rest (Fernet)
- `DatabaseTask` base class for Celery tasks avoids session leaks
- Batch aggregation in admin routes prevents N+1 queries
- `ReminderConfig` dataclass eliminates SIP/Loan code duplication
- Dev mode graceful degradation (returns fake success when WhatsApp not configured)

**Concerning patterns (future consideration):**
- Two parallel message-sending codepaths (`MessageService` vs campaign tasks) that may get out of sync
- Sync database engine with async FastAPI endpoints
- Campaign run marked "COMPLETED" after queueing, not after all sends complete
- `WhatsAppService` singleton adds no value for per-jeweller campaign sending

---

*Audit generated on April 12, 2026 — Revised for MVP reminder flow*
