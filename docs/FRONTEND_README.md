# 📱 EkTola Frontend Developer Guide

## WhatsApp Jeweller Platform - PWA Frontend Documentation

Welcome! This guide contains everything you need to build the Progressive Web App (PWA) frontend for EkTola.

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Getting Started](#getting-started)
3. [API Base URL & Documentation](#api-base-url--documentation)
4. [Authentication](#authentication)
5. [API Endpoints Reference](#api-endpoints-reference)
6. [TypeScript Types](#typescript-types)
7. [Error Handling](#error-handling)
8. [Recommended Tech Stack](#recommended-tech-stack)
9. [PWA Requirements](#pwa-requirements)

---

## 🎯 Project Overview

EkTola is a multi-tenant WhatsApp messaging platform for jewellers. The PWA allows jewellers to:

- **Register & Login** via phone number (WhatsApp OTP)
- **Manage Contacts** - Upload CSV/Excel, create, update, delete customers
- **Create Campaigns** - Schedule WhatsApp messages using templates
- **View Analytics** - Track message delivery rates, campaign performance
- **Admin Panel** - Manage templates, view cross-jeweller analytics

### User Roles

| Role | Description | Login Method |
|------|-------------|--------------|
| **Jeweller** | Business owner, manages contacts & campaigns | Phone + Password OR WhatsApp OTP |
| **Admin** | Platform admin, manages templates | Email + Password |

---

## 🚀 Getting Started

### 1. Run the Backend Locally

```bash
# Clone and setup backend
cd EkTola
pip install -r requirements.txt

# Configure environment variables (create .env file)
DATABASE_URL=postgresql://user:password@localhost:5432/ektola_db
SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Access API Documentation

| Resource | URL |
|----------|-----|
| **Swagger UI** (Interactive) | http://localhost:8000/docs |
| **ReDoc** (Clean docs) | http://localhost:8000/redoc |
| **OpenAPI JSON** | http://localhost:8000/openapi.json |

### 3. Generate TypeScript Types (Recommended)

```bash
# Install openapi-typescript
npm install -D openapi-typescript

# Generate types from running backend
npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts
```

---

## 🔗 API Base URL & Documentation

```
Base URL: http://localhost:8000
```

All endpoints return JSON. Include `Content-Type: application/json` header for POST/PATCH requests.

---

## 🔐 Authentication

### Token Format

The API uses **JWT Bearer tokens**. Include in request headers:

```http
Authorization: Bearer <access_token>
```

### Token Response Schema

```typescript
interface Token {
  access_token: string;   // Use this for API requests
  refresh_token: string;  // Use to get new access token
  token_type: "bearer";
}
```

### JWT Token Payload (Decoded)

```typescript
interface TokenData {
  user_id: number;
  email?: string;
  phone_number?: string;
  is_admin: boolean;
  jeweller_id?: number;  // null for admins
  exp: number;           // Expiration timestamp
}
```

---

## 🔑 Authentication Flows

### Jeweller Registration

```http
POST /auth/register
Content-Type: application/json

{
  "phone_number": "9876543210",    // 10 digits or +91 format
  "email": "shop@example.com",     // Optional
  "password": "securepassword",
  "business_name": "Krishna Jewellers"
}
```

**Response:** `201 Created` → `Token`

---

### Jeweller Login (Phone + Password)

```http
POST /auth/login/phone
Content-Type: application/json

{
  "phone_number": "9876543210",
  "password": "securepassword"
}
```

**Response:** `200 OK` → `Token`

---

### Jeweller Login (WhatsApp OTP)

**Step 1: Request OTP**

```http
POST /auth/otp/request/phone
Content-Type: application/json

{
  "phone_number": "9876543210"
}
```

**Response:** `200 OK`
```json
{
  "message": "OTP sent to WhatsApp",
  "otp": "123456"  // Only in development mode!
}
```

**Step 2: Verify OTP**

```http
POST /auth/otp/verify/phone
Content-Type: application/json

{
  "phone_number": "9876543210",
  "otp_code": "123456"
}
```

**Response:** `200 OK` → `Token`

---

### Admin Registration

```http
POST /auth/register-admin
Content-Type: application/json

{
  "email": "admin@ektola.com",
  "password": "secureadminpass",
  "full_name": "Admin User",
  "access_code": "<ADMIN_ACCESS_CODE>"  // Get from backend team
}
```

**Response:** `201 Created` → `Token`

---

### Admin Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "admin@ektola.com",
  "password": "secureadminpass"
}
```

**Response:** `200 OK` → `Token`

---

### Get Current User Profile

```http
GET /auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "email": "shop@example.com",
  "is_active": true,
  "is_admin": false,
  "created_at": "2026-02-04T10:00:00Z"
}
```

### Get Current Jeweller Profile

```http
GET /auth/me/jeweller
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "business_name": "Krishna Jewellers",
  "phone_number": "+919876543210",
  "is_approved": true,
  "is_active": true,
  "timezone": "Asia/Kolkata",
  "waba_id": null,
  "phone_number_id": null,
  "created_at": "2026-02-04T10:00:00Z"
}
```

---

## 📞 Contacts API

### Upload Contacts (Bulk - CSV/Excel)

```http
POST /contacts/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <contacts.csv or contacts.xlsx>
```

**Required CSV Columns:**
| Column | Type | Example |
|--------|------|---------|
| `phone_number` | string | `9876543210` |
| `segment` | enum | `GOLD_LOAN`, `GOLD_SIP`, `MARKETING` |
| `preferred_language` | enum | `en`, `hi`, `kn`, `ta`, `pa` |

**Optional Columns:** `name`, `customer_id`, `notes`, `tags`

**Response:** `200 OK`
```json
{
  "total_rows": 100,
  "imported": 85,
  "updated": 10,
  "failed": 5,
  "failure_details": [
    {"row": 23, "phone": "invalid", "reason": "Invalid phone number"}
  ]
}
```

---

### Create Single Contact

```http
POST /contacts/
Authorization: Bearer <token>
Content-Type: application/json

{
  "phone_number": "9876543210",
  "segment": "GOLD_LOAN",
  "preferred_language": "en",
  "name": "Ramesh Kumar",
  "customer_id": "CUST001",
  "notes": "VIP customer",
  "tags": "premium,regular"
}
```

**Response:** `201 Created` → `ContactResponse`

---

### List Contacts (Paginated)

```http
GET /contacts/?page=1&page_size=50&segment=GOLD_LOAN&opted_out=false&search=ramesh
Authorization: Bearer <token>
```

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number (1-indexed) |
| `page_size` | int | 50 | Items per page (max 100) |
| `segment` | enum | - | Filter by segment |
| `opted_out` | bool | - | Filter by opt-out status |
| `search` | string | - | Search name/phone |

**Response:**
```json
{
  "contacts": [
    {
      "id": 1,
      "jeweller_id": 1,
      "phone_number": "+919876543210",
      "name": "Ramesh Kumar",
      "customer_id": "CUST001",
      "segment": "GOLD_LOAN",
      "preferred_language": "en",
      "opted_out": false,
      "created_at": "2026-02-04T10:00:00Z",
      "updated_at": "2026-02-04T10:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 50,
  "total_pages": 3
}
```

---

### Get Contact Stats

```http
GET /contacts/stats
Authorization: Bearer <token>
```

**Response:**
```json
[
  {"segment": "GOLD_LOAN", "count": 50, "opted_out_count": 2},
  {"segment": "GOLD_SIP", "count": 30, "opted_out_count": 1},
  {"segment": "MARKETING", "count": 70, "opted_out_count": 5}
]
```

---

### Get/Update/Delete Single Contact

```http
GET    /contacts/{contact_id}
PATCH  /contacts/{contact_id}
DELETE /contacts/{contact_id}
Authorization: Bearer <token>
```

**PATCH Body (all fields optional):**
```json
{
  "name": "Updated Name",
  "segment": "GOLD_SIP",
  "preferred_language": "hi",
  "notes": "Updated notes",
  "opted_out": true
}
```

---

## 📢 Campaigns API

### Create Campaign

```http
POST /campaigns/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Monthly Gold Loan Reminder",
  "description": "Reminds customers about payment due dates",
  "campaign_type": "UTILITY",
  "sub_segment": "GOLD_LOAN",    // Required for UTILITY campaigns
  "template_id": 1,
  "recurrence_type": "MONTHLY",
  "start_date": "2026-02-01",
  "start_time": "10:00:00",
  "end_date": "2026-12-31",      // Optional
  "variable_mapping": {          // Optional - maps template vars to contact fields
    "customer_name": "name"
  }
}
```

**Response:** `201 Created` → `CampaignResponse`

---

### List Campaigns

```http
GET /campaigns/?page=1&page_size=20&status_filter=ACTIVE&campaign_type=UTILITY
Authorization: Bearer <token>
```

**Response:**
```json
{
  "campaigns": [...],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

---

### Campaign Lifecycle Actions

```http
GET    /campaigns/{id}              # Get campaign details
PATCH  /campaigns/{id}              # Update campaign
POST   /campaigns/{id}/activate     # Activate draft campaign
POST   /campaigns/{id}/pause        # Pause active campaign
POST   /campaigns/{id}/resume       # Resume paused campaign
DELETE /campaigns/{id}              # Delete (only DRAFT/COMPLETED)
```

---

### Get Campaign Runs (History)

```http
GET /campaigns/{id}/runs?limit=10
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": 1,
    "campaign_id": 5,
    "scheduled_at": "2026-02-01T10:00:00Z",
    "started_at": "2026-02-01T10:00:05Z",
    "completed_at": "2026-02-01T10:05:00Z",
    "status": "COMPLETED",
    "total_contacts": 100,
    "eligible_contacts": 98,
    "messages_queued": 98,
    "messages_sent": 98,
    "messages_delivered": 95,
    "messages_read": 80,
    "messages_failed": 3
  }
]
```

---

### Get Campaign Stats

```http
GET /campaigns/{id}/stats
Authorization: Bearer <token>
```

**Response:**
```json
{
  "campaign_id": 5,
  "campaign_name": "Monthly Gold Loan Reminder",
  "total_runs": 3,
  "total_messages_sent": 294,
  "total_delivered": 285,
  "total_read": 240,
  "total_failed": 9,
  "delivery_rate": 96.94,
  "read_rate": 84.21,
  "last_run_at": "2026-02-01T10:05:00Z",
  "next_run_at": "2026-03-01T10:00:00Z"
}
```

---

## 📝 Templates API (Jeweller - Read Only)

### List Available Templates

```http
GET /templates/?campaign_type=UTILITY
Authorization: Bearer <token>
```

**Response:**
```json
{
  "templates": [
    {
      "id": 1,
      "template_name": "gold_loan_reminder",
      "display_name": "Gold Loan Monthly Reminder",
      "campaign_type": "UTILITY",
      "sub_segment": "GOLD_LOAN",
      "description": "Reminder for gold loan payment",
      "category": "UTILITY",
      "is_active": true,
      "variable_count": 2,
      "variable_names": "customer_name,due_date",
      "translations": [
        {
          "id": 1,
          "language": "en",
          "header_text": null,
          "body_text": "Dear {{1}}, your gold loan payment is due on {{2}}.",
          "footer_text": "Thank you for banking with us.",
          "approval_status": "APPROVED"
        }
      ]
    }
  ],
  "total": 5
}
```

---

## 📝 Templates API (Admin - Full CRUD)

### Admin Endpoints

```http
GET    /templates/admin/all                        # List all templates (including inactive)
POST   /templates/admin/                           # Create template
PATCH  /templates/admin/{id}                       # Update template
DELETE /templates/admin/{id}                       # Soft delete template

# WhatsApp Sync
POST   /templates/admin/{id}/sync-to-whatsapp     # Submit to WhatsApp for approval
GET    /templates/admin/{id}/whatsapp-status      # Check approval status
POST   /templates/admin/sync-from-whatsapp        # Sync all templates from WhatsApp
DELETE /templates/admin/{id}/whatsapp             # Delete from WhatsApp
GET    /templates/admin/whatsapp-templates        # List templates directly from WhatsApp
```

### Create Template (Admin)

```http
POST /templates/admin/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "template_name": "gold_loan_reminder",
  "display_name": "Gold Loan Monthly Reminder",
  "campaign_type": "UTILITY",
  "sub_segment": "GOLD_LOAN",
  "description": "Reminder for gold loan payment",
  "category": "UTILITY",
  "variable_count": 2,
  "variable_names": ["customer_name", "due_date"],
  "translations": [
    {
      "language": "en",
      "header_text": null,
      "body_text": "Dear {{1}}, your gold loan payment is due on {{2}}.",
      "footer_text": "Thank you for banking with us."
    },
    {
      "language": "hi",
      "body_text": "प्रिय {{1}}, आपके गोल्ड लोन का भुगतान {{2}} को देय है।"
    }
  ]
}
```

---

## 📊 Analytics API

### Jeweller Dashboard

```http
GET /analytics/dashboard
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total_contacts": 150,
  "opted_out_contacts": 8,
  "active_campaigns": 3,
  "total_messages_sent": 1500,
  "recent_delivery_rate": 95.5,
  "recent_read_rate": 78.2,
  "contact_distribution": [
    {"segment": "GOLD_LOAN", "count": 50, "opted_out_count": 2}
  ],
  "recent_campaign_runs": [...]
}
```

---

### Admin Dashboard

```http
GET /analytics/admin/dashboard
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "total_jewellers": 25,
  "active_jewellers": 20,
  "total_contacts_across_jewellers": 5000,
  "total_messages_sent": 50000,
  "messages_last_30_days": 8000,
  "overall_delivery_rate": 94.5,
  "overall_read_rate": 75.0,
  "jeweller_stats": [
    {
      "jeweller_id": 1,
      "business_name": "Krishna Jewellers",
      "total_contacts": 150,
      "total_campaigns": 5,
      "total_messages_sent": 1500,
      "messages_last_30_days": 300,
      "delivery_rate": 95.5,
      "read_rate": 78.2,
      "last_active": "2026-02-04T10:00:00Z"
    }
  ]
}
```

---

### Admin Analytics (Detailed)

```http
GET /analytics/admin/analytics?days=30
Authorization: Bearer <admin_token>
```

---

## 🔔 Webhooks API (Internal Use)

The backend exposes webhook endpoints for WhatsApp status updates:

```http
POST /webhooks/whatsapp    # Receives WhatsApp callbacks
GET  /webhooks/whatsapp    # Webhook verification
```

---

## 📘 TypeScript Types

### Enums

```typescript
// src/types/enums.ts

export enum SegmentType {
  GOLD_LOAN = "GOLD_LOAN",
  GOLD_SIP = "GOLD_SIP",
  MARKETING = "MARKETING"
}

export enum CampaignType {
  UTILITY = "UTILITY",
  MARKETING = "MARKETING"
}

export enum CampaignStatus {
  DRAFT = "DRAFT",
  ACTIVE = "ACTIVE",
  PAUSED = "PAUSED",
  COMPLETED = "COMPLETED"
}

export enum MessageStatus {
  QUEUED = "QUEUED",
  SENT = "SENT",
  DELIVERED = "DELIVERED",
  READ = "READ",
  FAILED = "FAILED"
}

export enum RecurrenceType {
  DAILY = "DAILY",
  WEEKLY = "WEEKLY",
  MONTHLY = "MONTHLY",
  ONE_TIME = "ONE_TIME"
}

export enum Language {
  ENGLISH = "en",
  HINDI = "hi",
  KANNADA = "kn",
  TAMIL = "ta",
  PUNJABI = "pa"
}
```

### Common Interfaces

```typescript
// src/types/api.ts

interface Token {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

interface Contact {
  id: number;
  jeweller_id: number;
  phone_number: string;
  name?: string;
  customer_id?: string;
  segment: SegmentType;
  preferred_language: Language;
  opted_out: boolean;
  notes?: string;
  tags?: string;
  created_at: string;
  updated_at: string;
}

interface ContactListResponse {
  contacts: Contact[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface Campaign {
  id: number;
  jeweller_id: number;
  name: string;
  description?: string;
  campaign_type: CampaignType;
  sub_segment?: SegmentType;
  template_id: number;
  recurrence_type: RecurrenceType;
  start_date: string;      // YYYY-MM-DD
  start_time: string;      // HH:MM:SS
  end_date?: string;
  timezone: string;
  status: CampaignStatus;
  created_at: string;
  updated_at: string;
}

interface Template {
  id: number;
  template_name: string;
  display_name: string;
  campaign_type: CampaignType;
  sub_segment?: SegmentType;
  description?: string;
  category: string;
  is_active: boolean;
  variable_count: number;
  variable_names?: string;
  translations: TemplateTranslation[];
  created_at: string;
  updated_at: string;
}

interface TemplateTranslation {
  id: number;
  template_id: number;
  language: Language;
  header_text?: string;
  body_text: string;
  footer_text?: string;
  whatsapp_template_id?: string;
  approval_status: string;
  created_at: string;
}
```

---

## ⚠️ Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `204` | No Content (success, empty response) |
| `400` | Bad Request (validation error) |
| `401` | Unauthorized (invalid/missing token) |
| `403` | Forbidden (not allowed) |
| `404` | Not Found |
| `500` | Server Error |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Validation Error Format (400)

```json
{
  "detail": [
    {
      "loc": ["body", "phone_number"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Example: Token Refresh on 401

```typescript
async function apiRequest(url: string, options: RequestInit) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${getAccessToken()}`
    }
  });

  if (response.status === 401) {
    // Try to refresh token
    const newToken = await refreshAccessToken();
    if (newToken) {
      // Retry request with new token
      return fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'Authorization': `Bearer ${newToken}`
        }
      });
    }
    // Redirect to login
    window.location.href = '/login';
  }

  return response;
}
```

---

## 🛠️ Recommended Tech Stack

### For PWA Development

| Category | Recommendation |
|----------|----------------|
| **Framework** | React 18+ / Vue 3 / Svelte |
| **State Management** | Zustand / Pinia / React Query |
| **HTTP Client** | Axios / Fetch with wrapper |
| **Forms** | React Hook Form / Formik |
| **UI Components** | Tailwind CSS + Headless UI |
| **Date/Time** | date-fns / Day.js |
| **File Upload** | react-dropzone |
| **Charts** | Chart.js / Recharts |

### API Client Example (React Query + Axios)

```typescript
// src/api/client.ts
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json'
  }
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

```typescript
// src/api/contacts.ts
import { useQuery, useMutation } from '@tanstack/react-query';
import api from './client';

export const useContacts = (page = 1, segment?: string) => {
  return useQuery({
    queryKey: ['contacts', page, segment],
    queryFn: () => api.get('/contacts/', { 
      params: { page, segment } 
    }).then(res => res.data)
  });
};

export const useCreateContact = () => {
  return useMutation({
    mutationFn: (data) => api.post('/contacts/', data)
  });
};
```

---

## 📱 PWA Requirements

### manifest.json Example

```json
{
  "name": "EkTola - Jeweller WhatsApp",
  "short_name": "EkTola",
  "description": "Manage your jewellery business WhatsApp campaigns",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#D4AF37",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

### Service Worker Essentials

- Cache API responses for offline viewing
- Cache static assets (CSS, JS, images)
- Show offline page when network unavailable
- Background sync for pending actions

### Mobile-First Design

- Touch-friendly buttons (min 44x44px)
- Bottom navigation for primary actions
- Pull-to-refresh for lists
- Swipe actions for contact/campaign items
- Large input fields for phone numbers

---

## 🏗️ Suggested Page Structure

```
/                           → Dashboard (Jeweller)
/login                      → Login page (Phone + Password/OTP)
/register                   → Registration page
/contacts                   → Contact list with filters
/contacts/upload            → CSV/Excel upload
/contacts/:id               → Contact detail/edit
/campaigns                  → Campaign list
/campaigns/new              → Create campaign wizard
/campaigns/:id              → Campaign detail/stats
/templates                  → Browse templates
/settings                   → Profile settings

/admin                      → Admin dashboard
/admin/login                → Admin login
/admin/templates            → Template management
/admin/templates/new        → Create template
/admin/jewellers            → View all jewellers
```

---

## 📞 Support

For backend API questions, contact the backend team or check:
- Swagger UI: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

---

**Happy Coding! 🚀**
