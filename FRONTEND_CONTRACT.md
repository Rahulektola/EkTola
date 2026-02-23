# Frontend Developer Contract
## EkTola WhatsApp Jeweller Platform

---

## 🎯 What You Need to Build the TypeScript Frontend

This document provides everything needed to build a TypeScript frontend for the EkTola platform.

---

## 📦 TypeScript Types Reference

### Generate Types from OpenAPI

```bash
# Install openapi-typescript
npm install -D openapi-typescript

# Generate types from running backend
npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts
```

### API Documentation URLs
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 📋 Complete TypeScript Type Definitions

Copy these type definitions into your TypeScript frontend project.

### Enums (`types/enums.ts`)

```typescript
// ============ Contact Segment Types ============
export enum SegmentType {
  GOLD_LOAN = "GOLD_LOAN",
  GOLD_SIP = "GOLD_SIP",
  MARKETING = "MARKETING"
}

// ============ Campaign Types ============
export enum CampaignType {
  UTILITY = "UTILITY",
  MARKETING = "MARKETING"
}

// ============ Campaign Status ============
export enum CampaignStatus {
  DRAFT = "DRAFT",
  ACTIVE = "ACTIVE",
  PAUSED = "PAUSED",
  COMPLETED = "COMPLETED"
}

// ============ Message Status ============
export enum MessageStatus {
  QUEUED = "QUEUED",
  SENT = "SENT",
  DELIVERED = "DELIVERED",
  READ = "READ",
  FAILED = "FAILED"
}

// ============ Recurrence Types ============
export enum RecurrenceType {
  DAILY = "DAILY",
  WEEKLY = "WEEKLY",
  MONTHLY = "MONTHLY",
  ONE_TIME = "ONE_TIME"
}

// ============ Supported Languages ============
export enum Language {
  ENGLISH = "en",
  HINDI = "hi",
  KANNADA = "kn",
  TAMIL = "ta",
  PUNJABI = "pa"
}

// ============ Helper Functions ============
export const getLanguageLabel = (lang: Language): string => {
  const labels: Record<Language, string> = {
    [Language.ENGLISH]: "English",
    [Language.HINDI]: "हिंदी",
    [Language.KANNADA]: "ಕನ್ನಡ",
    [Language.TAMIL]: "தமிழ்",
    [Language.PUNJABI]: "ਪੰਜਾਬੀ"
  };
  return labels[lang] || lang;
};

export const getSegmentLabel = (segment: SegmentType): string => {
  const labels: Record<SegmentType, string> = {
    [SegmentType.GOLD_LOAN]: "Gold Loan",
    [SegmentType.GOLD_SIP]: "Gold SIP",
    [SegmentType.MARKETING]: "Marketing"
  };
  return labels[segment] || segment;
};
```

### Authentication Types (`types/auth.ts`)

```typescript
// ============ Token Types ============
export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface TokenData {
  user_id: number;
  email: string | null;
  phone_number: string | null;
  is_admin: boolean;
  jeweller_id: number | null;
  exp: number;
  type: "access" | "refresh";
}

// ============ Login Request Types ============
export interface LoginRequest {
  email: string;
  password: string;
}

export interface PhoneLoginRequest {
  phone_number: string;
  password: string;
}

// ============ OTP Request Types ============
export interface PhoneOTPRequest {
  phone_number: string;
}

export interface PhoneOTPVerifyRequest {
  phone_number: string;
  otp_code: string;
}

// ============ Registration Types ============
export interface RegisterRequest {
  email: string;
  password: string;
  business_name: string;
  phone_number: string;
}

export interface AdminRegisterRequest {
  email: string;
  password: string;
  full_name: string;
  access_code: string;
}

// ============ Response Types ============
export interface UserResponse {
  id: number;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string; // ISO datetime
}

export interface JewellerResponse {
  id: number;
  user_id: number;
  business_name: string;
  phone_number: string;
  is_approved: boolean;
  is_active: boolean;
  timezone: string;
  waba_id: string | null;
  phone_number_id: string | null;
  created_at: string; // ISO datetime
}

export interface OTPRequestResponse {
  message: string;
  otp?: string; // Only in development mode
}
```

### Contact Types (`types/contact.ts`)

```typescript
import { SegmentType, Language } from './enums';

export interface ContactCreate {
  phone_number: string;
  segment: SegmentType;
  preferred_language?: Language;
  name?: string;
  customer_id?: string;
  notes?: string;
  tags?: string;
}

export interface ContactUpdate {
  name?: string;
  segment?: SegmentType;
  preferred_language?: Language;
  notes?: string;
  tags?: string;
  opted_out?: boolean;
}

export interface ContactResponse {
  id: number;
  jeweller_id: number;
  phone_number: string;
  name: string | null;
  customer_id: string | null;
  segment: SegmentType;
  preferred_language: Language;
  opted_out: boolean;
  created_at: string;
  updated_at: string;
}

export interface ContactListResponse {
  contacts: ContactResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ContactListParams {
  page?: number;
  page_size?: number;
  segment?: SegmentType;
  search?: string;
  opted_out?: boolean;
}

export interface ContactSegmentStats {
  segment: SegmentType;
  count: number;
  opted_out_count: number;
}

export interface ContactImportReport {
  total_rows: number;
  imported: number;
  updated: number;
  failed: number;
  failure_details: Array<{
    row: number;
    phone: string;
    reason: string;
  }>;
}
```

### Campaign Types (`types/campaign.ts`)

```typescript
import { CampaignType, CampaignStatus, RecurrenceType, SegmentType } from './enums';

export interface CampaignCreate {
  name: string;
  description?: string;
  campaign_type: CampaignType;
  sub_segment?: SegmentType;
  template_id: number;
  recurrence_type: RecurrenceType;
  start_date: string; // "YYYY-MM-DD"
  start_time: string; // "HH:MM:SS"
  end_date?: string;
  variable_mapping?: Record<string, string>;
}

export interface CampaignUpdate {
  name?: string;
  description?: string;
  start_time?: string;
  end_date?: string;
  variable_mapping?: Record<string, string>;
}

export interface CampaignResponse {
  id: number;
  jeweller_id: number;
  name: string;
  description: string | null;
  campaign_type: CampaignType;
  sub_segment: SegmentType | null;
  template_id: number;
  recurrence_type: RecurrenceType;
  start_date: string;
  start_time: string;
  end_date: string | null;
  timezone: string;
  status: CampaignStatus;
  created_at: string;
  updated_at: string;
}

export interface CampaignListResponse {
  campaigns: CampaignResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface CampaignListParams {
  page?: number;
  page_size?: number;
  status_filter?: CampaignStatus;
  campaign_type?: CampaignType;
}

export interface CampaignRunResponse {
  id: number;
  campaign_id: number;
  scheduled_at: string;
  started_at: string | null;
  completed_at: string | null;
  status: string;
  total_contacts: number;
  eligible_contacts: number;
  messages_queued: number;
  messages_sent: number;
  messages_delivered: number;
  messages_read: number;
  messages_failed: number;
}

export interface CampaignStatsResponse {
  campaign_id: number;
  campaign_name: string;
  total_runs: number;
  total_messages_sent: number;
  total_delivered: number;
  total_read: number;
  total_failed: number;
  delivery_rate: number;
  read_rate: number;
  last_run_at: string | null;
  next_run_at: string | null;
}
```

### Template Types (`types/template.ts`)

```typescript
import { CampaignType, SegmentType, Language } from './enums';

export interface TemplateTranslationCreate {
  language: Language;
  header_text?: string;
  body_text: string;
  footer_text?: string;
}

export interface TemplateTranslationResponse {
  id: number;
  template_id: number;
  language: Language;
  header_text: string | null;
  body_text: string;
  footer_text: string | null;
  whatsapp_template_id: string | null;
  approval_status: string;
  created_at: string;
}

export interface TemplateCreate {
  template_name: string;
  display_name: string;
  campaign_type: CampaignType;
  sub_segment?: SegmentType;
  description?: string;
  category: "UTILITY" | "MARKETING" | "AUTHENTICATION";
  variable_count?: number;
  variable_names?: string[];
  translations: TemplateTranslationCreate[];
}

export interface TemplateUpdate {
  display_name?: string;
  description?: string;
  is_active?: boolean;
}

export interface TemplateResponse {
  id: number;
  template_name: string;
  display_name: string;
  campaign_type: CampaignType;
  sub_segment: SegmentType | null;
  description: string | null;
  category: string;
  is_active: boolean;
  variable_count: number;
  variable_names: string | null;
  translations: TemplateTranslationResponse[];
  created_at: string;
  updated_at: string;
}

export interface TemplateListResponse {
  templates: TemplateResponse[];
  total: number;
}
```

### Message Types (`types/message.ts`)

```typescript
import { MessageStatus, Language } from './enums';

export interface MessageResponse {
  id: number;
  jeweller_id: number;
  contact_id: number;
  campaign_run_id: number | null;
  phone_number: string;
  template_name: string;
  language: Language;
  whatsapp_message_id: string | null;
  status: MessageStatus;
  queued_at: string;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  failed_at: string | null;
  failure_reason: string | null;
  retry_count: number;
}

export interface MessageStatsResponse {
  total_messages: number;
  queued: number;
  sent: number;
  delivered: number;
  read: number;
  failed: number;
  delivery_rate: number;
  read_rate: number;
}

export interface FailureBreakdown {
  failure_reason: string;
  count: number;
}
```

### Analytics Types (`types/analytics.ts`)

```typescript
import { ContactSegmentStats } from './contact';
import { CampaignStatsResponse } from './campaign';
import { FailureBreakdown } from './message';

export interface JewellerDashboardResponse {
  total_contacts: number;
  opted_out_contacts: number;
  active_campaigns: number;
  total_messages_sent: number;
  recent_delivery_rate: number;
  recent_read_rate: number;
  contact_distribution: ContactSegmentStats[];
  recent_campaign_runs: CampaignStatsResponse[];
}

export interface JewellerUsageStats {
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

export interface AdminDashboardResponse {
  total_jewellers: number;
  active_jewellers: number;
  total_contacts_across_jewellers: number;
  total_messages_sent: number;
  messages_last_30_days: number;
  overall_delivery_rate: number;
  overall_read_rate: number;
  jeweller_stats: JewellerUsageStats[];
}

export interface LanguageDistribution {
  language: string;
  message_count: number;
  percentage: number;
}

export interface CampaignTypeDistribution {
  campaign_type: string;
  count: number;
  percentage: number;
}

export interface AdminAnalyticsResponse {
  total_messages: number;
  language_distribution: LanguageDistribution[];
  campaign_type_distribution: CampaignTypeDistribution[];
  failure_breakdown: FailureBreakdown[];
  daily_message_volume: Array<{ date: string; count: number }>;
}
```

### API Helper Types (`types/api.ts`)

```typescript
export interface ApiError {
  detail: string;
  status_code?: number;
}

export interface ValidationError {
  detail: Array<{
    loc: (string | number)[];
    msg: string;
    type: string;
  }>;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}
```

---

## 🔐 Authentication Flow

### JWT Token Structure

**Login Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Token Payload (Decoded):**
```json
{
  "user_id": 123,
  "email": "jeweller@example.com",
  "phone_number": "+919876543210",
  "is_admin": false,
  "jeweller_id": 45,
  "exp": 1706112000,
  "type": "access"
}
```

**Token Lifetime:**
- Access Token: 30 minutes
- Refresh Token: 7 days

### Authentication Methods

**Jeweller Login Options:**
1. Phone + Password: `POST /auth/login/phone`
2. WhatsApp OTP: `POST /auth/otp/request/phone` → `POST /auth/otp/verify/phone`

**Admin Login:**
1. Email + Password: `POST /auth/login`

---

## 📡 API Endpoints Reference

### Base URL
```
Development: http://localhost:8000
```

### Authentication Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/auth/register` | Register jeweller | `RegisterRequest` | `Token` |
| POST | `/auth/register-admin` | Register admin | `AdminRegisterRequest` | `Token` |
| POST | `/auth/login` | Admin email login | `LoginRequest` | `Token` |
| POST | `/auth/login/phone` | Jeweller phone login | `PhoneLoginRequest` | `Token` |
| POST | `/auth/otp/request/phone` | Request WhatsApp OTP | `PhoneOTPRequest` | `OTPRequestResponse` |
| POST | `/auth/otp/verify/phone` | Verify OTP & login | `PhoneOTPVerifyRequest` | `Token` |
| GET | `/auth/me` | Get user profile | - | `UserResponse` |
| GET | `/auth/me/jeweller` | Get jeweller profile | - | `JewellerResponse` |

### Contact Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/contacts/` | Create contact | `ContactCreate` | `ContactResponse` |
| GET | `/contacts/` | List contacts | Query params | `ContactListResponse` |
| GET | `/contacts/{id}` | Get contact | - | `ContactResponse` |
| PATCH | `/contacts/{id}` | Update contact | `ContactUpdate` | `ContactResponse` |
| DELETE | `/contacts/{id}` | Delete contact | - | 204 |
| GET | `/contacts/stats` | Get segment stats | - | `ContactSegmentStats[]` |
| POST | `/contacts/upload` | Upload CSV/XLSX | FormData | `ContactImportReport` |

### Campaign Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/campaigns/` | Create campaign | `CampaignCreate` | `CampaignResponse` |
| GET | `/campaigns/` | List campaigns | Query params | `CampaignListResponse` |
| GET | `/campaigns/{id}` | Get campaign | - | `CampaignResponse` |
| PATCH | `/campaigns/{id}` | Update campaign | `CampaignUpdate` | `CampaignResponse` |
| DELETE | `/campaigns/{id}` | Delete campaign | - | 204 |
| POST | `/campaigns/{id}/activate` | Activate | - | `CampaignResponse` |
| POST | `/campaigns/{id}/pause` | Pause | - | `CampaignResponse` |
| POST | `/campaigns/{id}/resume` | Resume | - | `CampaignResponse` |
| GET | `/campaigns/{id}/stats` | Get stats | - | `CampaignStatsResponse` |
| GET | `/campaigns/{id}/runs` | Get runs | - | `CampaignRunResponse[]` |

### Template Endpoints (Admin)

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/templates/` | Create template | `TemplateCreate` | `TemplateResponse` |
| GET | `/templates/` | List templates | Query params | `TemplateListResponse` |
| GET | `/templates/{id}` | Get template | - | `TemplateResponse` |
| PATCH | `/templates/{id}` | Update template | `TemplateUpdate` | `TemplateResponse` |
| DELETE | `/templates/{id}` | Delete template | - | 204 |
| POST | `/templates/sync` | Sync from WhatsApp | - | `{ synced, created, updated }` |

### Analytics Endpoints

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/analytics/dashboard` | Jeweller dashboard | `JewellerDashboardResponse` |
| GET | `/analytics/admin/dashboard` | Admin dashboard | `AdminDashboardResponse` |
| GET | `/analytics/admin/analytics` | Admin analytics | `AdminAnalyticsResponse` |

---

## 🚨 Error Handling

### Standard Error Response
```typescript
interface ApiError {
  detail: string;
}
```

### Validation Error Response
```typescript
interface ValidationError {
  detail: Array<{
    loc: (string | number)[];
    msg: string;
    type: string;
  }>;
}
```

### HTTP Status Codes
- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Success with no body
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Invalid/missing token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error (detailed)

---

## 📱 File Upload

### Contact Upload (CSV/XLSX)

**Endpoint:** `POST /contacts/upload`

**Request:**
```typescript
const formData = new FormData();
formData.append('file', file);

const response = await fetch('/contacts/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

**CSV Format:**
```csv
phone_number,segment,preferred_language,name,customer_id
+919876543210,GOLD_LOAN,en,John Doe,CUST001
+919876543211,GOLD_SIP,hi,Jane Smith,CUST002
```

**Required columns:** `phone_number`, `segment`, `preferred_language`
**Optional columns:** `name`, `customer_id`, `notes`, `tags`

---

## 🔧 API Client Example

```typescript
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  private getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) url.searchParams.append(key, String(value));
      });
    }
    const response = await fetch(url.toString(), { headers: this.getHeaders() });
    if (!response.ok) throw await response.json();
    return response.json();
  }

  async post<T>(endpoint: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) throw await response.json();
    if (response.status === 204) return undefined as T;
    return response.json();
  }

  async patch<T>(endpoint: string, body: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify(body),
    });
    if (!response.ok) throw await response.json();
    return response.json();
  }

  async delete(endpoint: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });
    if (!response.ok) throw await response.json();
  }

  async uploadFile<T>(endpoint: string, file: File): Promise<T> {
    const formData = new FormData();
    formData.append('file', file);
    const headers: HeadersInit = {};
    const token = this.getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!response.ok) throw await response.json();
    return response.json();
  }
}

export const api = new ApiClient();
```

---

## ✅ Frontend Developer Checklist

### Setup
- [ ] Download OpenAPI spec from `/openapi.json`
- [ ] Copy TypeScript types from this document
- [ ] Set up API client with auth headers
- [ ] Configure environment variables

### Authentication
- [ ] Implement phone login form
- [ ] Implement WhatsApp OTP flow
- [ ] Store tokens securely
- [ ] Handle token expiration (401)

### Features
- [ ] Contact upload (CSV/XLSX)
- [ ] Contact list with pagination
- [ ] Campaign creation wizard
- [ ] Campaign management (activate/pause)
- [ ] Dashboard with analytics

### PWA
- [ ] Add manifest.json
- [ ] Implement service worker
- [ ] Offline fallback page
- [ ] Mobile-responsive design

---

**Last Updated**: February 5, 2026  
**Backend Version**: 1.1.0  
**API Docs**: http://localhost:8000/docs
