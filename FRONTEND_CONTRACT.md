# Frontend Developer Contract
## EkTola WhatsApp Jeweller Platform

---

## 🎯 What You Need to Build the PWA

Your frontend developer needs these files and documentation to build the Progressive Web App without waiting for the full backend implementation.

---

## 📦 Files to Share

### 1. **API Contract** (AUTO-GENERATED)

**Primary Source: OpenAPI Specification**

Once you run the backend locally, share:
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc`

Your frontend dev can:
1. Generate TypeScript types automatically
2. Generate API client code
3. See all request/response examples
4. Test endpoints interactively

### 2. **TypeScript Type Generation** (RECOMMENDED)

Install and run `openapi-typescript` to generate TypeScript interfaces:

```bash
# In frontend project
npm install -D openapi-typescript

# Generate types from running backend
npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts

# Or from downloaded openapi.json file
npx openapi-typescript ./openapi.json -o src/types/api.ts
```

This creates a complete TypeScript type file with all API schemas.

### 3. **Shared Files** (Copy these from backend)

**Must Share:**
- `app/utils/enums.py` → Convert to TypeScript enums
- `app/schemas/*.py` → Reference for understanding data structures

**TypeScript Enum Conversion:**
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
  "is_admin": false,
  "jeweller_id": 45,
  "exp": 1706112000,
  "type": "access"
}
```

**Token Lifetime:**
- Access Token: 30 minutes
- Refresh Token: 7 days

### Frontend Implementation

```typescript
// Example: src/services/auth.ts
class AuthService {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  async login(email: string, password: string) {
    const response = await fetch('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
    
    // Store in localStorage or secure storage
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    
    return data;
  }

  getAuthHeader() {
    const token = localStorage.getItem('access_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  async apiCall(url: string, options: RequestInit = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        ...this.getAuthHeader()
      }
    });
    
    if (response.status === 401) {
      // Handle token refresh or redirect to login
      this.logout();
    }
    
    return response;
  }

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.accessToken = null;
    this.refreshToken = null;
  }
}
```

---

## 📡 API Endpoints Reference

### Base URL
```
Development: http://localhost:8000
Production: https://api.ektola.com (TBD)
```

### Authentication Endpoints

```typescript
// Register Jeweller
POST /auth/register
Body: {
  email: string;
  password: string;
  business_name: string;
  phone_number: string;
}
Response: { access_token, refresh_token, token_type }

// Login
POST /auth/login
Body: { email: string; password: string }
Response: { access_token, refresh_token, token_type }

// Request OTP
POST /auth/otp/request
Body: { email: string }
Response: { message: string, otp?: string } // otp only in dev

// Verify OTP
POST /auth/otp/verify
Body: { email: string; otp_code: string }
Response: { access_token, refresh_token, token_type }

// Get Profile
GET /auth/me
Headers: { Authorization: "Bearer <token>" }
Response: UserResponse

// Get Jeweller Profile
GET /auth/me/jeweller
Headers: { Authorization: "Bearer <token>" }
Response: JewellerResponse
```

### Contact Management

```typescript
// Upload Contacts (CSV/XLSX)
POST /contacts/upload
Headers: { Authorization: "Bearer <token>" }
Body: FormData with file
Response: ContactImportReport

// Create Single Contact
POST /contacts/
Body: ContactCreate
Response: ContactResponse

// List Contacts (Paginated)
GET /contacts/?page=1&page_size=50&segment=GOLD_LOAN&search=john
Response: ContactListResponse

// Get Contact Stats
GET /contacts/stats
Response: ContactSegmentStats[]

// Get Contact
GET /contacts/{id}
Response: ContactResponse

// Update Contact
PATCH /contacts/{id}
Body: ContactUpdate (partial)
Response: ContactResponse

// Delete Contact
DELETE /contacts/{id}
Response: 204 No Content
```

### Campaign Management

```typescript
// Create Campaign
POST /campaigns/
Body: CampaignCreate
Response: CampaignResponse

// List Campaigns
GET /campaigns/?page=1&status_filter=ACTIVE&campaign_type=UTILITY
Response: CampaignListResponse

// Get Campaign
GET /campaigns/{id}
Response: CampaignResponse

// Update Campaign
PATCH /campaigns/{id}
Body: CampaignUpdate
Response: CampaignResponse

// Activate Campaign
POST /campaigns/{id}/activate
Response: CampaignResponse

// Pause Campaign
POST /campaigns/{id}/pause
Response: CampaignResponse

// Resume Campaign
POST /campaigns/{id}/resume
Response: CampaignResponse

// Get Campaign Runs
GET /campaigns/{id}/runs?limit=10
Response: CampaignRunResponse[]

// Get Campaign Stats
GET /campaigns/{id}/stats
Response: CampaignStatsResponse

// Delete Campaign
DELETE /campaigns/{id}
Response: 204 No Content
```

### Templates

```typescript
// List Templates (Jeweller)
GET /templates/?campaign_type=UTILITY
Response: TemplateListResponse

// Get Template (Jeweller)
GET /templates/{id}
Response: TemplateResponse
```

### Analytics

```typescript
// Jeweller Dashboard
GET /analytics/dashboard
Response: JewellerDashboardResponse

// Admin Dashboard (Admin only)
GET /analytics/admin/dashboard
Response: AdminDashboardResponse

// Admin Detailed Analytics (Admin only)
GET /analytics/admin/detailed?days=30
Response: AdminAnalyticsResponse
```

---

## 📋 Key Data Models (TypeScript Interfaces)

### Contact
```typescript
interface ContactResponse {
  id: number;
  jeweller_id: number;
  phone_number: string;
  name: string | null;
  customer_id: string | null;
  segment: SegmentType;
  preferred_language: Language;
  opted_out: boolean;
  created_at: string; // ISO 8601
  updated_at: string;
}

interface ContactCreate {
  phone_number: string;
  segment: SegmentType;
  preferred_language: Language;
  name?: string;
  customer_id?: string;
  notes?: string;
  tags?: string;
}
```

### Campaign
```typescript
interface CampaignResponse {
  id: number;
  jeweller_id: number;
  name: string;
  description: string | null;
  campaign_type: CampaignType;
  sub_segment: SegmentType | null;
  template_id: number;
  recurrence_type: RecurrenceType;
  start_date: string; // YYYY-MM-DD
  start_time: string; // HH:MM:SS
  end_date: string | null;
  timezone: string;
  status: CampaignStatus;
  created_at: string;
  updated_at: string;
}

interface CampaignCreate {
  name: string;
  description?: string;
  campaign_type: CampaignType;
  sub_segment?: SegmentType; // Required if campaign_type is UTILITY
  template_id: number;
  recurrence_type: RecurrenceType;
  start_date: string; // YYYY-MM-DD
  start_time: string; // HH:MM:SS
  end_date?: string;
  variable_mapping?: Record<string, string>;
}
```

### Dashboard
```typescript
interface JewellerDashboardResponse {
  total_contacts: number;
  opted_out_contacts: number;
  active_campaigns: number;
  total_messages_sent: number;
  recent_delivery_rate: number; // Percentage
  recent_read_rate: number; // Percentage
  contact_distribution: ContactSegmentStats[];
  recent_campaign_runs: CampaignStatsResponse[];
}

interface ContactSegmentStats {
  segment: SegmentType;
  count: number;
  opted_out_count: number;
}
```

---

## 🚨 Error Handling

### Standard Error Response
```json
{
  "detail": "Error message here"
}
```

### Common Status Codes
- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Success with no response body
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error (detailed)

### Frontend Error Handling Example
```typescript
async function handleApiCall<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options?.headers,
      ...authService.getAuthHeader()
    }
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API request failed');
  }

  return response.json();
}
```

---

## 📱 File Upload Pattern

### Contact Upload (CSV/XLSX)

**Frontend Implementation:**
```typescript
async function uploadContacts(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8000/contacts/upload', {
    method: 'POST',
    headers: {
      ...authService.getAuthHeader()
      // Don't set Content-Type - browser will set it with boundary
    },
    body: formData
  });

  const result: ContactImportReport = await response.json();
  return result;
}
```

**Expected Response:**
```json
{
  "total_rows": 100,
  "imported": 85,
  "updated": 10,
  "failed": 5,
  "failure_details": [
    {
      "row": 23,
      "phone": "+1234567890",
      "reason": "Invalid segment: INVALID_VALUE"
    }
  ]
}
```

---

## 🧪 Mock Data for Development

While backend is being built, use these mock responses:

```typescript
// src/mocks/api.ts
export const mockDashboard: JewellerDashboardResponse = {
  total_contacts: 1250,
  opted_out_contacts: 45,
  active_campaigns: 3,
  total_messages_sent: 5430,
  recent_delivery_rate: 94.5,
  recent_read_rate: 67.8,
  contact_distribution: [
    { segment: SegmentType.GOLD_LOAN, count: 500, opted_out_count: 20 },
    { segment: SegmentType.GOLD_SIP, count: 450, opted_out_count: 15 },
    { segment: SegmentType.MARKETING, count: 300, opted_out_count: 10 }
  ],
  recent_campaign_runs: []
};
```

---

## ✅ Checklist for Frontend Developer

### Setup Phase
- [ ] Clone/receive this documentation
- [ ] Install backend locally (or get access to dev server)
- [ ] Download OpenAPI JSON from `/openapi.json`
- [ ] Generate TypeScript types using `openapi-typescript`
- [ ] Copy TypeScript enums from this document
- [ ] Set up environment variables (API base URL)

### Development Phase
- [ ] Implement authentication service (login, OTP, token storage)
- [ ] Create API client wrapper with auth headers
- [ ] Build contact upload UI (CSV/XLSX)
- [ ] Build contact list with pagination & filters
- [ ] Build campaign creation form
- [ ] Build campaign list & management UI
- [ ] Build dashboard with analytics
- [ ] Implement error handling
- [ ] Add loading states
- [ ] Test with mock data first
- [ ] Integrate with live backend

### PWA Requirements
- [ ] Add manifest.json
- [ ] Implement service worker
- [ ] Add "Add to Home Screen" prompt
- [ ] Optimize for mobile (touch targets, responsive)
- [ ] Test on low-end Android devices
- [ ] Implement offline fallback pages
- [ ] Add loading indicators for slow networks

---

## 🔗 Communication Points

### What Frontend Dev Can Start Immediately
1. ✅ Authentication UI (login, register, OTP)
2. ✅ Contact list UI with pagination
3. ✅ Campaign creation form
4. ✅ Dashboard layout
5. ✅ File upload component

### What Requires Backend Coordination
1. ⏳ WhatsApp Business Account setup UI (depends on WABA integration)
2. ⏳ Real-time message status updates (needs WebSocket or polling strategy)
3. ⏳ Template preview (needs actual WhatsApp template data)

### Regular Sync Points
- **Daily**: API changes, enum updates, validation rules
- **Weekly**: New endpoints, schema changes, error handling patterns

---

## 📞 Questions Frontend Dev Might Have

**Q: How do I know if a user is admin vs jeweller?**  
A: Decode the JWT token. Check `is_admin` and `jeweller_id` fields.

**Q: How do I handle token refresh?**  
A: Not implemented in MVP. For now, redirect to login on 401. Post-MVP: implement refresh token flow.

**Q: Can I use the Swagger UI for testing?**  
A: Yes! Go to `http://localhost:8000/docs`, click "Authorize", paste your token, and test all endpoints interactively.

**Q: What's the CSV format for contact upload?**  
A: Required columns: `phone_number`, `segment`, `preferred_language`. Optional: `name`, `customer_id`, `notes`, `tags`. See example in `/contacts/upload` docs.

**Q: How do I handle file size limits?**  
A: Not enforced yet in backend. Recommend client-side limit of 10MB or 10,000 rows.

**Q: What date/time format should I use?**  
A: Send dates as `YYYY-MM-DD`, times as `HH:MM:SS` (24-hour), datetimes as ISO 8601 strings.

---

## 🎁 Bonus: Example API Client

```typescript
// src/services/api-client.ts
import { AuthService } from './auth';

class ApiClient {
  private baseUrl: string;
  private authService: AuthService;

  constructor(baseUrl: string, authService: AuthService) {
    this.baseUrl = baseUrl;
    this.authService = authService;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
        ...this.authService.getAuthHeader()
      }
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail);
    }

    if (response.status === 204) {
      return null as T;
    }

    return response.json();
  }

  // Contacts
  async getContacts(params?: { page?: number; segment?: string }) {
    const query = new URLSearchParams(params as any).toString();
    return this.request<ContactListResponse>(`/contacts/?${query}`);
  }

  async createContact(data: ContactCreate) {
    return this.request<ContactResponse>('/contacts/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async uploadContacts(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${this.baseUrl}/contacts/upload`, {
      method: 'POST',
      headers: this.authService.getAuthHeader(),
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }

    return response.json() as Promise<ContactImportReport>;
  }

  // Campaigns
  async getCampaigns(params?: { page?: number; status_filter?: string }) {
    const query = new URLSearchParams(params as any).toString();
    return this.request<CampaignListResponse>(`/campaigns/?${query}`);
  }

  async createCampaign(data: CampaignCreate) {
    return this.request<CampaignResponse>('/campaigns/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async pauseCampaign(id: number) {
    return this.request<CampaignResponse>(`/campaigns/${id}/pause`, {
      method: 'POST'
    });
  }

  // Dashboard
  async getDashboard() {
    return this.request<JewellerDashboardResponse>('/analytics/dashboard');
  }
}

export default ApiClient;
```

---

## 📚 Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **OpenAPI Spec**: https://swagger.io/specification/
- **WhatsApp Cloud API**: https://developers.facebook.com/docs/whatsapp/cloud-api/
- **PWA Guidelines**: https://web.dev/progressive-web-apps/

---

**Last Updated**: January 24, 2026  
**Backend Version**: 1.0.0  
**Contact**: Backend Developer (You!)
