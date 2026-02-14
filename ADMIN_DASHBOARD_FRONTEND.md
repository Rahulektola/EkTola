# EkTola Admin Dashboard — Frontend Developer Guide

> **Base URL:** `http://localhost:8000` (dev) | Swagger docs at `/docs`
> **Auth:** All admin endpoints require `Authorization: Bearer <token>` header

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Authentication](#2-authentication)
3. [Admin Dashboard Pages & API Map](#3-admin-dashboard-pages--api-map)
4. [API Reference — Complete Endpoint List](#4-api-reference--complete-endpoint-list)
5. [Data Models & TypeScript Interfaces](#5-data-models--typescript-interfaces)
6. [Enums (use these exact string values)](#6-enums)
7. [Suggested Page Structure & UI Components](#7-suggested-page-structure--ui-components)
8. [Impersonation Mode](#8-impersonation-mode)
9. [Error Handling](#9-error-handling)
10. [CORS & Environment](#10-cors--environment)

---

## 1. Architecture Overview

EkTola is a WhatsApp campaign platform for jewellers. The **admin dashboard** lets the EkTola team:

- Review & approve/reject jeweller registrations
- View/edit jeweller profiles, contacts, campaigns, messages
- Upload contacts on behalf of jewellers (CSV/Excel)
- Create & start campaigns for jewellers
- View cross-jeweller analytics and per-jeweller drill-downs
- Impersonate a jeweller ("Login As") to see their dashboard

**Backend stack:** FastAPI + SQLAlchemy + MySQL + Redis + Celery

---

## 2. Authentication

### 2.1 Admin Login

```
POST /auth/login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "approval_status": null,
  "rejection_reason": null
}
```

### 2.2 Admin Registration (one-time setup)

```
POST /auth/register-admin
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "securepassword",
  "full_name": "Admin Name",
  "access_code": "<server-side ADMIN_ACCESS_CODE>"
}
```

### 2.3 Using the Token

Include on **every** admin request:
```
Authorization: Bearer <access_token>
```

### 2.4 JWT Payload Structure

```json
{
  "user_id": 1,
  "email": "admin@example.com",
  "is_admin": true,
  "jeweller_id": null
}
```

- `access_token` expires in **30 minutes**
- `refresh_token` expires in **7 days**
- Use `POST /auth/refresh` with the refresh token to get a new access token

### 2.5 Token Refresh

```
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOi..."
}
```

---

## 3. Admin Dashboard Pages & API Map

| Page | Primary Endpoint(s) | Description |
|------|---------------------|-------------|
| **Dashboard Home** | `GET /analytics/admin/dashboard` | KPI cards + per-jeweller usage table |
| **Detailed Analytics** | `GET /analytics/admin/detailed?days=30` | Language/campaign breakdowns, failure analysis, daily volume chart |
| **Jeweller List** | `GET /admin/jewellers?page=1&page_size=20&status=PENDING&q=search` | Paginated, filterable, searchable list |
| **Pending Approvals** | `GET /admin/jewellers/pending` | Quick-access: all pending jewellers |
| **Jeweller Detail** | `GET /admin/jewellers/{id}` | Full profile + aggregate stats |
| **Jeweller Analytics** | `GET /admin/jewellers/{id}/analytics?days=30` | Per-jeweller drill-down charts |
| **Jeweller Contacts** | `GET /admin/jewellers/{id}/contacts?page=1&segment=GOLD_LOAN&q=search` | Contact list for a jeweller |
| **Jeweller Campaigns** | `GET /admin/jewellers/{id}/campaigns?page=1&status=ACTIVE` | Campaign list for a jeweller |
| **Jeweller Messages** | `GET /admin/jewellers/{id}/messages?page=1&status=DELIVERED` | Message history for a jeweller |
| **Impersonate** | `POST /admin/impersonate/{id}` | Get token to view jeweller's dashboard |

---

## 4. API Reference — Complete Endpoint List

### 4.1 Jeweller Management

#### List Jewellers (paginated, filterable, searchable)
```
GET /admin/jewellers
```
| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `page` | int | 1 | Page number (≥1) |
| `page_size` | int | 20 | Items per page (1–100) |
| `status` | string | — | Filter: `PENDING`, `APPROVED`, `REJECTED` |
| `q` | string | — | Search by business name, owner name, or phone |
| `sort_by` | string | `created_at` | Sort field (any Jeweller column) |
| `sort_order` | string | `desc` | `asc` or `desc` |

**Response:** `JewellerListResponse` (includes `pending_count`, `approved_count`, `rejected_count` for filter badges)

---

#### Get Pending Jewellers
```
GET /admin/jewellers/pending
```
Convenience shortcut — returns all pending jewellers without pagination.

---

#### Get Jeweller Detail
```
GET /admin/jewellers/{jeweller_id}
```
Returns full profile with `total_contacts`, `total_campaigns`, `total_messages`, `email`.

---

#### Update Jeweller Profile
```
PATCH /admin/jewellers/{jeweller_id}
Content-Type: application/json

{
  "business_name": "New Name",     // optional
  "owner_name": "Owner",           // optional
  "phone_number": "+919876543210", // optional
  "address": "...",                // optional
  "location": "...",               // optional
  "is_whatsapp_business": true,    // optional
  "timezone": "Asia/Kolkata",      // optional
  "is_active": true                // optional
}
```
All fields are optional — only send what you want to change.

---

#### Update Admin Notes (internal, hidden from jeweller)
```
PUT /admin/jewellers/{jeweller_id}/notes
Content-Type: application/json

{
  "admin_notes": "VIP client, priority support"
}
```

---

#### Update Meta/WhatsApp Integration
```
PUT /admin/jewellers/{jeweller_id}/meta-status
Content-Type: application/json

{
  "waba_id": "...",               // optional
  "phone_number_id": "...",       // optional
  "access_token": "...",          // optional
  "webhook_verify_token": "...",  // optional
  "is_whatsapp_business": true,   // optional
  "meta_app_status": true         // optional
}
```

---

#### Approve Jeweller
```
POST /admin/jewellers/{jeweller_id}/approve
```
**Response:**
```json
{
  "id": 1,
  "business_name": "Gold Palace",
  "approval_status": "APPROVED",
  "approved_at": "2026-02-10T12:00:00",
  "message": "Jeweller 'Gold Palace' has been approved successfully."
}
```
Returns `400` if already approved.

---

#### Reject Jeweller
```
POST /admin/jewellers/{jeweller_id}/reject
Content-Type: application/json

{
  "rejection_reason": "Incomplete business documents"
}
```
`rejection_reason` is **mandatory** (min 5 characters). Stored and visible to the jeweller.

---

#### Delete Jeweller
```
DELETE /admin/jewellers/{jeweller_id}
```
**Cascading delete** — removes jeweller, associated user account, and all related data.

**Response:**
```json
{ "message": "Jeweller deleted successfully", "jeweller_id": 1 }
```

---

### 4.2 Contact Management

#### List Jeweller's Contacts
```
GET /admin/jewellers/{jeweller_id}/contacts
```
| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page (1–100) |
| `segment` | string | — | `GOLD_LOAN`, `GOLD_SIP`, `MARKETING` |
| `q` | string | — | Search by name or phone |

---

#### Upload Contacts (CSV/Excel)
```
POST /admin/jewellers/{jeweller_id}/contacts/upload
Content-Type: multipart/form-data

file: <CSV or Excel file>
```
**Required CSV columns:** `Name`, `Mobile`, `Purpose` (`SIP` / `LOAN` / `BOTH`)
**Optional column:** `Date`

**Response:**
```json
{
  "total_rows": 100,
  "imported": 85,
  "updated": 10,
  "failed": 5,
  "failure_details": [
    { "row": 12, "name": "John", "mobile": "invalid", "reason": "Invalid mobile number" }
  ],
  "jeweller_id": 1,
  "jeweller_name": "Gold Palace",
  "message": "Upload completed for Gold Palace"
}
```

---

#### Edit Contact
```
PATCH /admin/contacts/{contact_id}
```
| Query Param | Type | Description |
|-------------|------|-------------|
| `name` | string | Contact name |
| `phone_number` | string | Phone number |
| `segment` | string | `GOLD_LOAN` / `GOLD_SIP` / `MARKETING` |
| `preferred_language` | string | `en` / `hi` / `kn` / `ta` / `pa` |
| `opted_out` | bool | Opt-out status |
| `notes` | string | Notes |
| `tags` | string | Tags |

All fields are **query parameters** (not JSON body).

---

#### Delete Contact (soft delete)
```
DELETE /admin/contacts/{contact_id}
```

---

### 4.3 Campaign Management

#### List Jeweller's Campaigns
```
GET /admin/jewellers/{jeweller_id}/campaigns
```
| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | (1–100) |
| `status` | string | — | `DRAFT`, `ACTIVE`, `PAUSED`, `COMPLETED` |

---

#### Create Campaign for Jeweller
```
POST /admin/jewellers/{jeweller_id}/campaigns
Content-Type: application/json

{
  "name": "Gold Loan Reminder",
  "description": "Monthly reminder for gold loan customers",
  "campaign_type": "UTILITY",
  "sub_segment": "GOLD_LOAN",
  "template_id": 1,
  "recurrence_type": "MONTHLY",
  "start_date": "2026-03-01",
  "start_time": "09:00:00",
  "end_date": "2026-12-31",
  "variable_mapping": { "1": "name", "2": "amount" }
}
```
- `campaign_type`: `UTILITY` or `MARKETING`
- If `UTILITY`, `sub_segment` is **required**
- `recurrence_type`: `DAILY`, `WEEKLY`, `MONTHLY`, `ONE_TIME`
- Jeweller must be **approved** to create campaigns
- Campaign is created in `DRAFT` status

**Response:**
```json
{
  "id": 42,
  "jeweller_id": 1,
  "name": "Gold Loan Reminder",
  "status": "DRAFT",
  "message": "Campaign 'Gold Loan Reminder' created for Gold Palace"
}
```

---

#### Start/Activate Campaign
```
POST /admin/campaigns/{campaign_id}/start
```
Changes campaign status from `DRAFT` → `ACTIVE`. Returns `400` if already active.

---

### 4.4 Message History

#### View Jeweller's Messages
```
GET /admin/jewellers/{jeweller_id}/messages
```
| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 50 | (1–200) |
| `status` | string | — | `QUEUED`, `SENT`, `DELIVERED`, `READ`, `FAILED` |

---

### 4.5 Impersonation

```
POST /admin/impersonate/{jeweller_id}
```
Returns a scoped JWT token that lets the admin access **jeweller-facing** endpoints as if they were that jeweller.

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "jeweller_id": 1,
  "jeweller_name": "Gold Palace",
  "message": "Impersonating jeweller 'Gold Palace'. Use this token for jeweller endpoints."
}
```

Use the returned `access_token` in the `Authorization` header to call jeweller endpoints (`/contacts`, `/campaigns`, `/analytics/dashboard`, etc.).

---

### 4.6 Analytics

#### Admin Dashboard Overview
```
GET /analytics/admin/dashboard
```
**Response:**
```json
{
  "total_jewellers": 50,
  "active_jewellers": 42,
  "total_contacts_across_jewellers": 15000,
  "total_messages_sent": 120000,
  "messages_last_30_days": 8500,
  "overall_delivery_rate": 94.5,
  "overall_read_rate": 67.2,
  "jeweller_stats": [
    {
      "jeweller_id": 1,
      "business_name": "Gold Palace",
      "total_contacts": 500,
      "total_campaigns": 12,
      "total_messages_sent": 5000,
      "messages_last_30_days": 350,
      "delivery_rate": 96.0,
      "read_rate": 72.5,
      "last_active": "2026-02-10T14:30:00"
    }
  ]
}
```

---

#### Detailed Admin Analytics
```
GET /analytics/admin/detailed?days=30
```
| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `days` | int | 30 | Lookback period (1–365) |

**Response:**
```json
{
  "total_messages": 8500,
  "language_distribution": [
    { "language": "en", "message_count": 5000, "percentage": 58.82 },
    { "language": "hi", "message_count": 2500, "percentage": 29.41 }
  ],
  "campaign_type_distribution": [
    { "campaign_type": "UTILITY", "count": 30, "percentage": 60.0 },
    { "campaign_type": "MARKETING", "count": 20, "percentage": 40.0 }
  ],
  "failure_breakdown": [
    { "failure_reason": "Invalid phone number", "count": 45 }
  ],
  "daily_message_volume": [
    { "date": "2026-02-01", "count": 250 },
    { "date": "2026-02-02", "count": 310 }
  ]
}
```

---

#### Per-Jeweller Analytics Drill-down
```
GET /admin/jewellers/{jeweller_id}/analytics?days=30
```
**Response:**
```json
{
  "jeweller_id": 1,
  "business_name": "Gold Palace",
  "total_contacts": 500,
  "opted_out_contacts": 12,
  "total_campaigns": 12,
  "active_campaigns": 3,
  "total_messages": 5000,
  "messages_last_30_days": 350,
  "delivery_rate": 96.0,
  "read_rate": 72.5,
  "campaign_success_rates": [
    {
      "campaign_id": 5,
      "campaign_name": "Monthly SIP Reminder",
      "run_id": 101,
      "messages_sent": 200,
      "delivered": 195,
      "read": 140,
      "failed": 5,
      "delivery_rate": 97.5,
      "read_rate": 71.79,
      "completed_at": "2026-02-10T10:00:00"
    }
  ],
  "daily_message_volume": [
    { "date": "2026-02-01", "count": 15 }
  ]
}
```

---

## 5. Data Models & TypeScript Interfaces

```typescript
// ===================== ENUMS =====================

type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED";
type SegmentType = "GOLD_LOAN" | "GOLD_SIP" | "MARKETING";
type CampaignType = "UTILITY" | "MARKETING";
type CampaignStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "COMPLETED";
type MessageStatus = "QUEUED" | "SENT" | "DELIVERED" | "READ" | "FAILED";
type RecurrenceType = "DAILY" | "WEEKLY" | "MONTHLY" | "ONE_TIME";
type Language = "en" | "hi" | "kn" | "ta" | "pa";

// ===================== AUTH =====================

interface Token {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  approval_status: ApprovalStatus | null;
  rejection_reason: string | null;
}

interface LoginRequest {
  email: string;
  password: string;
}

// ===================== JEWELLER =====================

interface JewellerDetail {
  id: number;
  user_id: number;
  business_name: string;
  owner_name: string | null;
  phone_number: string;
  address: string | null;
  location: string | null;
  waba_id: string | null;
  phone_number_id: string | null;
  is_whatsapp_business: boolean;
  meta_app_status: boolean;
  is_approved: boolean;
  approval_status: ApprovalStatus;
  rejection_reason: string | null;
  approved_at: string | null;        // ISO datetime
  approved_by_user_id: number | null;
  is_active: boolean;
  admin_notes: string | null;
  timezone: string;
  created_at: string;                // ISO datetime
  updated_at: string;                // ISO datetime
  total_contacts: number;
  total_campaigns: number;
  total_messages: number;
  email: string | null;
}

interface JewellerListResponse {
  jewellers: JewellerDetail[];
  total: number;
  page: number;
  page_size: number;
  pending_count: number;
  approved_count: number;
  rejected_count: number;
}

interface JewellerUpdateRequest {
  business_name?: string;
  owner_name?: string;
  phone_number?: string;
  address?: string;
  location?: string;
  is_whatsapp_business?: boolean;
  timezone?: string;
  is_active?: boolean;
}

interface MetaStatusUpdateRequest {
  waba_id?: string;
  phone_number_id?: string;
  access_token?: string;
  webhook_verify_token?: string;
  is_whatsapp_business?: boolean;
  meta_app_status?: boolean;
}

interface ApproveJewellerResponse {
  id: number;
  business_name: string;
  approval_status: ApprovalStatus;
  rejection_reason: string | null;
  approved_at: string | null;
  message: string;
}

// ===================== CONTACTS =====================

interface AdminContact {
  id: number;
  jeweller_id: number;
  phone_number: string;
  name: string | null;
  customer_id: string | null;
  segment: SegmentType;
  preferred_language: Language;
  opted_out: boolean;
  notes: string | null;
  tags: string | null;
  created_at: string;
  updated_at: string;
}

interface AdminContactsPage {
  contacts: AdminContact[];
  total: number;
  page: number;
  page_size: number;
  jeweller_id: number;
  jeweller_name: string;
}

interface ContactUploadResult {
  total_rows: number;
  imported: number;
  updated: number;
  failed: number;
  failure_details: Array<{
    row: number;
    name: string;
    mobile: string;
    reason: string;
  }>;
  jeweller_id: number;
  jeweller_name: string;
  message: string;
}

// ===================== CAMPAIGNS =====================

interface AdminCampaign {
  id: number;
  jeweller_id: number;
  name: string;
  description: string | null;
  campaign_type: CampaignType;
  sub_segment: SegmentType | null;
  status: CampaignStatus;
  template_id: number;
  recurrence_type: string;
  start_date: string;
  start_time: string;
  end_date: string | null;
  created_at: string;
  updated_at: string;
  total_runs: number;
  total_messages_sent: number;
}

interface AdminCampaignsPage {
  campaigns: AdminCampaign[];
  total: number;
  page: number;
  page_size: number;
  jeweller_id: number;
  jeweller_name: string;
}

interface AdminCampaignCreateRequest {
  name: string;
  description?: string;
  campaign_type: CampaignType;
  sub_segment?: SegmentType;           // required if UTILITY
  template_id: number;
  recurrence_type: RecurrenceType;
  start_date: string;                  // "YYYY-MM-DD"
  start_time: string;                  // "HH:MM:SS"
  end_date?: string;                   // "YYYY-MM-DD"
  variable_mapping?: Record<string, string>;
}

// ===================== MESSAGES =====================

interface AdminMessage {
  id: number;
  jeweller_id: number;
  contact_id: number;
  phone_number: string;
  template_name: string;
  language: string;
  message_body: string;
  status: string;
  whatsapp_message_id: string | null;
  queued_at: string;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  failed_at: string | null;
  failure_reason: string | null;
}

interface AdminMessagesPage {
  messages: AdminMessage[];
  total: number;
  page: number;
  page_size: number;
  jeweller_id: number;
}

// ===================== IMPERSONATION =====================

interface ImpersonateResponse {
  access_token: string;
  token_type: "bearer";
  jeweller_id: number;
  jeweller_name: string;
  message: string;
}

// ===================== ANALYTICS =====================

interface JewellerUsageStats {
  jeweller_id: number;
  business_name: string;
  total_contacts: number;
  total_campaigns: number;
  total_messages_sent: number;
  messages_last_30_days: number;
  delivery_rate: number;
  read_rate: number;
  last_active: string | null;
}

interface AdminDashboardResponse {
  total_jewellers: number;
  active_jewellers: number;
  total_contacts_across_jewellers: number;
  total_messages_sent: number;
  messages_last_30_days: number;
  overall_delivery_rate: number;
  overall_read_rate: number;
  jeweller_stats: JewellerUsageStats[];
}

interface AdminAnalyticsResponse {
  total_messages: number;
  language_distribution: Array<{
    language: string;
    message_count: number;
    percentage: number;
  }>;
  campaign_type_distribution: Array<{
    campaign_type: string;
    count: number;
    percentage: number;
  }>;
  failure_breakdown: Array<{
    failure_reason: string;
    count: number;
  }>;
  daily_message_volume: Array<{
    date: string;
    count: number;
  }>;
}

interface JewellerAnalyticsResponse {
  jeweller_id: number;
  business_name: string;
  total_contacts: number;
  opted_out_contacts: number;
  total_campaigns: number;
  active_campaigns: number;
  total_messages: number;
  messages_last_30_days: number;
  delivery_rate: number;
  read_rate: number;
  campaign_success_rates: Array<{
    campaign_id: number;
    campaign_name: string;
    run_id: number;
    messages_sent: number;
    delivered: number;
    read: number;
    failed: number;
    delivery_rate: number;
    read_rate: number;
    completed_at: string;
  }>;
  daily_message_volume: Array<{
    date: string;
    count: number;
  }>;
}
```

---

## 6. Enums

Use these **exact string values** in API requests and expect them in responses:

| Enum | Values |
|------|--------|
| **ApprovalStatus** | `PENDING`, `APPROVED`, `REJECTED` |
| **SegmentType** | `GOLD_LOAN`, `GOLD_SIP`, `MARKETING` |
| **CampaignType** | `UTILITY`, `MARKETING` |
| **CampaignStatus** | `DRAFT`, `ACTIVE`, `PAUSED`, `COMPLETED` |
| **MessageStatus** | `QUEUED`, `SENT`, `DELIVERED`, `READ`, `FAILED` |
| **RecurrenceType** | `DAILY`, `WEEKLY`, `MONTHLY`, `ONE_TIME` |
| **Language** | `en` (English), `hi` (Hindi), `kn` (Kannada), `ta` (Tamil), `pa` (Punjabi) |

---

## 7. Suggested Page Structure & UI Components

### 7.1 Recommended Route Map

```
/admin
├── /dashboard                → Admin Dashboard Home (KPI cards + jeweller table)
├── /analytics                → Detailed Analytics (charts, breakdowns)
├── /jewellers                → Jeweller List (filterable table)
│   ├── ?status=PENDING       → Filter by status via query param
│   └── /:id                  → Jeweller Detail Page
│       ├── /contacts         → Jeweller's contact list
│       ├── /campaigns        → Jeweller's campaign list
│       ├── /messages         → Jeweller's message history
│       └── /analytics        → Jeweller drill-down analytics
└── /impersonate/:id          → Switch to jeweller view
```

### 7.2 Dashboard Home (`/admin/dashboard`)

**API:** `GET /analytics/admin/dashboard`

| Component | Data Source |
|-----------|------------|
| KPI Card: Total Jewellers | `total_jewellers` |
| KPI Card: Active Jewellers | `active_jewellers` |
| KPI Card: Total Contacts | `total_contacts_across_jewellers` |
| KPI Card: Messages (30d) | `messages_last_30_days` |
| KPI Card: Delivery Rate | `overall_delivery_rate` (show as %) |
| KPI Card: Read Rate | `overall_read_rate` (show as %) |
| Jeweller Usage Table | `jeweller_stats[]` — sortable columns |

### 7.3 Jeweller List (`/admin/jewellers`)

**API:** `GET /admin/jewellers`

| Component | Details |
|-----------|---------|
| Status filter tabs | Use `pending_count`, `approved_count`, `rejected_count` as badge counts |
| Search bar | Sends `q` param — searches business name, owner name, phone |
| Sortable table columns | `business_name`, `phone_number`, `approval_status`, `created_at`, `total_contacts`, `total_campaigns` |
| Pagination | `page`, `page_size`, `total` |
| Row actions | View Detail, Approve, Reject, Delete, Impersonate |

### 7.4 Jeweller Detail (`/admin/jewellers/:id`)

**API:** `GET /admin/jewellers/{id}`

| Section | Fields |
|---------|--------|
| Profile Info | `business_name`, `owner_name`, `phone_number`, `email`, `address`, `location`, `timezone` |
| Approval Status | Badge showing `approval_status`, `rejection_reason` if rejected, `approved_at` |
| WhatsApp Integration | `waba_id`, `phone_number_id`, `is_whatsapp_business`, `meta_app_status` |
| Stats Summary | `total_contacts`, `total_campaigns`, `total_messages` |
| Admin Notes | Editable textarea → `PUT /admin/jewellers/{id}/notes` |
| Action Buttons | Edit Profile, Approve/Reject, Update Meta, Impersonate, Delete |

### 7.5 Contact Upload Modal

**API:** `POST /admin/jewellers/{id}/contacts/upload`

- File input accepting `.csv`, `.xlsx`, `.xls`
- Show upload results: imported / updated / failed counts
- Display failure table with row number, name, mobile, reason

### 7.6 Analytics Page (`/admin/analytics`)

**API:** `GET /analytics/admin/detailed?days=30`

| Chart | Data |
|-------|------|
| Daily Message Volume (line chart) | `daily_message_volume` |
| Language Distribution (pie/donut) | `language_distribution` |
| Campaign Type Distribution (pie/donut) | `campaign_type_distribution` |
| Failure Reasons (bar chart) | `failure_breakdown` |
| Days selector | 7 / 30 / 90 / 365 |

---

## 8. Impersonation Mode

Impersonation lets an admin "become" a jeweller to see their exact dashboard view.

### Flow:
1. Admin clicks **"Login As"** on a jeweller row
2. Frontend calls `POST /admin/impersonate/{jeweller_id}`
3. Backend returns a scoped JWT with `jeweller_id` set
4. Frontend stores this token separately (e.g., `sessionStorage`)
5. Frontend switches to the **jeweller dashboard** view using this token
6. Show a persistent banner: *"Viewing as Gold Palace — [Exit Impersonation]"*
7. On exit, restore the admin token and return to admin dashboard

### Important:
- The impersonation token has `is_admin: false` so jeweller endpoints accept it
- The token includes `impersonated_by` (admin user_id) for audit
- Impersonation token follows the same 30-minute expiry

---

## 9. Error Handling

All errors follow this pattern:

```json
{
  "detail": "Human-readable error message"
}
```

| HTTP Code | Meaning |
|-----------|---------|
| `400` | Bad request (validation error, already approved, etc.) |
| `401` | Unauthorized (missing/invalid token) |
| `403` | Forbidden (not an admin) |
| `404` | Resource not found (jeweller, contact, campaign) |
| `422` | Validation error (Pydantic) — includes field-level details |

### 422 Validation Error Format:
```json
{
  "detail": [
    {
      "loc": ["body", "rejection_reason"],
      "msg": "String should have at least 5 characters",
      "type": "string_too_short"
    }
  ]
}
```

---

## 10. CORS & Environment

- **CORS:** Currently allows all origins (`*`) — no CORS issues in development
- **API Docs (Swagger):** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`
- **Health check:** `GET /health` → `{ "status": "healthy", "environment": "development" }`

### Running the backend locally:
```bash
pip install -r requirements.txt
# Set up .env with DATABASE_URL, SECRET_KEY, REDIS_URL
python -m uvicorn app.main:app --reload --port 8000
```

---

## Quick Reference — All Admin Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/admin/jewellers` | List jewellers (paginated, filterable) |
| `GET` | `/admin/jewellers/pending` | Pending jewellers only |
| `GET` | `/admin/jewellers/{id}` | Jeweller detail |
| `PATCH` | `/admin/jewellers/{id}` | Edit jeweller profile |
| `PUT` | `/admin/jewellers/{id}/notes` | Update admin notes |
| `PUT` | `/admin/jewellers/{id}/meta-status` | Update WhatsApp integration |
| `POST` | `/admin/jewellers/{id}/approve` | Approve jeweller |
| `POST` | `/admin/jewellers/{id}/reject` | Reject jeweller |
| `DELETE` | `/admin/jewellers/{id}` | Delete jeweller |
| `GET` | `/admin/jewellers/{id}/contacts` | Jeweller's contacts |
| `POST` | `/admin/jewellers/{id}/contacts/upload` | Upload contacts CSV/Excel |
| `PATCH` | `/admin/contacts/{id}` | Edit contact |
| `DELETE` | `/admin/contacts/{id}` | Delete contact |
| `GET` | `/admin/jewellers/{id}/campaigns` | Jeweller's campaigns |
| `POST` | `/admin/jewellers/{id}/campaigns` | Create campaign for jeweller |
| `POST` | `/admin/campaigns/{id}/start` | Activate campaign |
| `GET` | `/admin/jewellers/{id}/messages` | Jeweller's message history |
| `POST` | `/admin/impersonate/{id}` | Impersonate jeweller |
| `GET` | `/admin/jewellers/{id}/analytics` | Jeweller analytics drill-down |
| `GET` | `/analytics/admin/dashboard` | Admin dashboard overview |
| `GET` | `/analytics/admin/detailed` | Detailed analytics + charts |
