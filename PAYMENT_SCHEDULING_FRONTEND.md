# Payment Reminder Scheduling — Frontend Integration Guide

> **Audience:** Frontend developer working on the Jeweller Dashboard (Contacts page)  
> **Backend version:** EkTola API — March 2026  
> **Timezone:** All dates/times are Indian Standard Time (IST, UTC+5:30)

---

## Overview

Jewellers can assign a **monthly payment due date** (day 1–31) for each Gold SIP and Gold Loan customer. The system automatically sends a WhatsApp reminder **N days before** the due date (default 3, configurable 1–15). Only contacts with an assigned payment day receive reminders — contacts with `null` payment days are skipped entirely.

### Key Rules

- **SIP schedules** can only be set on contacts with segment `GOLD_SIP` or `BOTH`
- **Loan schedules** can only be set on contacts with segment `GOLD_LOAN` or `BOTH`
- `BOTH` segment contacts can have both SIP and Loan schedules
- `MARKETING` contacts cannot have payment schedules
- Month-end handling: if a contact has payment day 31 but the month only has 30 days, the system treats the due date as the last day of the month

---

## Authentication

All endpoints require a Bearer JWT token:

```
Authorization: Bearer <access_token>
```

The token must belong to an **active, approved jeweller user** (not an admin).

| Error | Code | When |
|-------|------|------|
| Missing/invalid token | `401` | Token expired, malformed, or absent |
| Admin user | `403` | Admin users cannot access jeweller endpoints |
| Unapproved jeweller | `403` | Jeweller account pending approval |

---

## New Fields on Contact Responses

**All existing contact endpoints** (list, detail, create, update) now include these fields in every `ContactResponse`:

```json
{
  "id": 42,
  "name": "Rahul Sharma",
  "phone_number": "+919876543210",
  "segment": "GOLD_SIP",
  "preferred_language": "en",
  "opted_out": false,

  "sip_payment_day": 5,
  "loan_payment_day": null,
  "sip_reminder_days_before": 3,
  "loan_reminder_days_before": 3,
  "last_sip_reminder_sent_at": "2026-02-02T03:30:00",
  "last_loan_reminder_sent_at": null,

  "created_at": "2025-12-01T10:00:00",
  "updated_at": "2026-03-01T14:22:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `sip_payment_day` | `int \| null` | Day of month (1–31) for SIP payment. `null` = no schedule. |
| `loan_payment_day` | `int \| null` | Day of month (1–31) for Loan payment. `null` = no schedule. |
| `sip_reminder_days_before` | `int` | Days before SIP due date to send reminder. Default `3`. |
| `loan_reminder_days_before` | `int` | Days before Loan due date to send reminder. Default `3`. |
| `last_sip_reminder_sent_at` | `datetime \| null` | When the last SIP reminder was sent. `null` = never sent. |
| `last_loan_reminder_sent_at` | `datetime \| null` | When the last Loan reminder was sent. `null` = never sent. |

> **Tip:** You can also set `sip_payment_day` and `loan_payment_day` through the existing `PATCH /contacts/{id}` endpoint using the normal contact update body.

---

## API Endpoints

### 1. Set Payment Schedule (Single Contact)

```
PUT /contacts/{contact_id}/payment-schedule
```

Set or update the SIP/Loan payment day and reminder lead time for one contact.

**Request Body:**
```json
{
  "sip_payment_day": 5,
  "loan_payment_day": null,
  "sip_reminder_days_before": 3,
  "loan_reminder_days_before": 3
}
```

All fields are **optional** — only send the ones you want to change.  
Set a day to `null` to clear it (stops reminders for that type).

| Field | Type | Range | Notes |
|-------|------|-------|-------|
| `sip_payment_day` | `int \| null` | 1–31 | Requires segment `GOLD_SIP` or `BOTH` |
| `loan_payment_day` | `int \| null` | 1–31 | Requires segment `GOLD_LOAN` or `BOTH` |
| `sip_reminder_days_before` | `int` | 1–15 | |
| `loan_reminder_days_before` | `int` | 1–15 | |

**Response:** `200 OK` — full `ContactResponse` with updated fields.

**Errors:**

| Code | Reason |
|------|--------|
| `400` | Segment mismatch (e.g., setting SIP day on a `GOLD_LOAN` contact) |
| `404` | Contact not found or doesn't belong to this jeweller |

**Example:**
```js
const res = await fetch(`/contacts/42/payment-schedule`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    sip_payment_day: 10,
    sip_reminder_days_before: 2,
  }),
});
const contact = await res.json();
// contact.sip_payment_day === 10
```

---

### 2. Clear Payment Schedule

```
DELETE /contacts/{contact_id}/payment-schedule
```

Explicitly clear SIP and/or Loan schedules. Resets both the payment day and the last-reminder-sent timestamp.

**Request Body:**
```json
{
  "clear_sip": true,
  "clear_loan": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `clear_sip` | `bool` | `false` | Clear SIP schedule and reset `last_sip_reminder_sent_at` |
| `clear_loan` | `bool` | `false` | Clear Loan schedule and reset `last_loan_reminder_sent_at` |

**Response:** `200 OK` — full `ContactResponse`.

**Example:**
```js
await fetch(`/contacts/42/payment-schedule`, {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ clear_sip: true }),
});
```

---

### 3. Bulk Update Payment Schedules

```
POST /contacts/bulk-payment-schedule
```

Update payment schedules for up to **500 contacts** in a single request. Supports partial success — individual failures are reported, the rest are committed.

**Request Body:**
```json
{
  "schedules": [
    { "contact_id": 42, "sip_payment_day": 5 },
    { "contact_id": 43, "loan_payment_day": 15, "loan_reminder_days_before": 5 },
    { "contact_id": 44, "sip_payment_day": 10, "loan_payment_day": 20 }
  ]
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `schedules` | `array` | Min 1, max 500 items |
| `schedules[].contact_id` | `int` | **Required** |
| `schedules[].sip_payment_day` | `int \| null` | 1–31 |
| `schedules[].loan_payment_day` | `int \| null` | 1–31 |
| `schedules[].sip_reminder_days_before` | `int` | 1–15 |
| `schedules[].loan_reminder_days_before` | `int` | 1–15 |

**Response:** `200 OK`
```json
{
  "updated": 2,
  "failed": 1,
  "failure_details": [
    { "contact_id": 43, "reason": "Loan schedule requires GOLD_LOAN or BOTH segment" }
  ],
  "message": "Updated 2 schedule(s), 1 failed"
}
```

---

### 4. List Payment Schedules

```
GET /contacts/payment-schedules
```

Paginated list of contacts with their payment schedule info. Useful for a dedicated "Payment Schedules" tab or view.

**Query Parameters:**

| Param | Type | Default | Values |
|-------|------|---------|--------|
| `schedule_type` | `string` | — | `sip`, `loan`, `all` |
| `has_schedule` | `bool` | — | `true` = only scheduled, `false` = only unscheduled |
| `page` | `int` | `1` | ≥ 1 |
| `page_size` | `int` | `50` | 1–100 |

**Response:** `200 OK`
```json
{
  "contacts": [
    {
      "contact_id": 42,
      "name": "Rahul Sharma",
      "phone_number": "+919876543210",
      "segment": "GOLD_SIP",
      "sip_payment_day": 5,
      "loan_payment_day": null,
      "sip_reminder_days_before": 3,
      "loan_reminder_days_before": 3,
      "last_sip_reminder_sent_at": "2026-02-02T03:30:00",
      "last_loan_reminder_sent_at": null
    }
  ],
  "total": 85,
  "page": 1,
  "page_size": 50,
  "total_pages": 2
}
```

**Filter Examples:**
```
GET /contacts/payment-schedules?schedule_type=sip&has_schedule=true
GET /contacts/payment-schedules?schedule_type=loan&has_schedule=false&page=2
GET /contacts/payment-schedules?has_schedule=true
```

> Excludes opted-out and deleted contacts automatically. Sorted by name.

---

### 5. Reminder Preview

```
GET /contacts/reminder-preview
```

Shows which contacts will receive payment reminders **today**. Helps jewellers see what's about to go out.

**Response:** `200 OK`
```json
{
  "sip_reminders_due_today": 3,
  "loan_reminders_due_today": 1,
  "sip_contacts": [
    {
      "contact_id": 42,
      "name": "Rahul Sharma",
      "phone_number": "+919876543210",
      "segment": "GOLD_SIP",
      "sip_payment_day": 5,
      "loan_payment_day": null,
      "sip_reminder_days_before": 3,
      "loan_reminder_days_before": 3,
      "last_sip_reminder_sent_at": null,
      "last_loan_reminder_sent_at": null
    }
  ],
  "loan_contacts": [
    {
      "contact_id": 50,
      "name": "Priya Patel",
      "phone_number": "+919876501234",
      "segment": "GOLD_LOAN",
      "sip_payment_day": null,
      "loan_payment_day": 8,
      "sip_reminder_days_before": 3,
      "loan_reminder_days_before": 5,
      "last_sip_reminder_sent_at": null,
      "last_loan_reminder_sent_at": null
    }
  ]
}
```

---

## UI Implementation Guide

### A. Contact Table — New Columns

Add these columns to the contacts list table:

| Column Header | Source Field | Display |
|---------------|-------------|---------|
| SIP Due Date | `sip_payment_day` | Show as ordinal: "5th", "15th". Show "—" if `null`. |
| Loan Due Date | `loan_payment_day` | Same as above. Show "—" if `null`. |
| Last SIP Reminder | `last_sip_reminder_sent_at` | Relative time: "2 days ago", or "Never" if `null`. |
| Last Loan Reminder | `last_loan_reminder_sent_at` | Same as above. |

### B. Contact Detail / Edit Modal — Payment Schedule Section

Add a "Payment Schedule" section below the contact info form:

```
┌─────────────────────────────────────────────────────────────┐
│  Payment Schedule                                           │
│                                                             │
│  SIP Payment Day:  [ 5  ▼]   Remind: [ 3 ▼] days before   │
│  Loan Payment Day: [ —  ▼]   Remind: [ 3 ▼] days before   │
│                                                             │
│  [Save Schedule]   [Clear SIP]  [Clear Loan]                │
│                                                             │
│  Last SIP reminder: 2 Mar 2026, 9:00 AM                     │
│  Last Loan reminder: Never                                  │
└─────────────────────────────────────────────────────────────┘
```

- **SIP Day dropdown:** Numbers 1–31 + "Not scheduled" option (`null`)
- **Loan Day dropdown:** Same
- **Remind dropdown:** Numbers 1–15 (days before)
- Only show SIP fields for `GOLD_SIP` / `BOTH` contacts
- Only show Loan fields for `GOLD_LOAN` / `BOTH` contacts
- Disable/hide irrelevant fields based on segment

### C. Bulk Schedule Assignment

Add a toolbar action when multiple contacts are selected:

1. User selects contacts in the table (checkboxes)
2. Clicks "Set Payment Dates"
3. Modal opens with day/reminder pickers
4. Submits to `POST /contacts/bulk-payment-schedule`
5. Shows success/failure summary from response

### D. Reminder Preview Widget

Add a small card/banner at the top of the Contacts page:

```
┌──────────────────────────────────────────┐
│  📅 Today's Reminders                    │
│  SIP: 3 customers  |  Loan: 1 customer   │
│  [View Details]                           │
└──────────────────────────────────────────┘
```

Calls `GET /contacts/reminder-preview` on page load. Clicking "View Details" shows the list of contacts receiving reminders today.

---

## Segment-to-Schedule Mapping Quick Reference

| Contact Segment | Can Set SIP Date? | Can Set Loan Date? |
|-----------------|--------------------|--------------------|
| `GOLD_SIP` | Yes | No |
| `GOLD_LOAN` | No | Yes |
| `BOTH` | Yes | Yes |
| `MARKETING` | No | No |

---

## How Reminders Work (Background)

1. **Daily at 9:00 AM IST**, a background job runs automatically
2. For each contact with a payment day set, the system calculates:
   - `reminder_date = payment_day − reminder_days_before` (clamped to last day of month)
3. If today equals the `reminder_date` AND no reminder has been sent this month → sends a WhatsApp template message
4. The `last_sip_reminder_sent_at` / `last_loan_reminder_sent_at` field updates after a successful send
5. If a customer has `sip_payment_day = null` → **no SIP reminder is ever sent**

### Example Timeline

| Setting | Value |
|---------|-------|
| `sip_payment_day` | `10` |
| `sip_reminder_days_before` | `3` |

- Reminder sent on: **7th** of every month at 9:00 AM IST
- If February (28 days) and `payment_day = 31` → effective due date = Feb 28 → reminder on Feb 25

---

## Error Handling Reference

| Endpoint | Error Code | Response Body | Cause |
|----------|------------|---------------|-------|
| All | `401` | `{"detail": "..."}` | Invalid/expired token |
| All | `403` | `{"detail": "..."}` | Not an approved jeweller |
| PUT schedule | `400` | `{"detail": "SIP payment schedule can only be set for GOLD_SIP or BOTH contacts"}` | Wrong segment |
| PUT schedule | `400` | `{"detail": "Loan payment schedule can only be set for GOLD_LOAN or BOTH contacts"}` | Wrong segment |
| PUT/DELETE | `404` | `{"detail": "Contact not found"}` | Invalid contact_id or not owned by jeweller |
| Any | `422` | `{"detail": [...]}` | Pydantic validation (day out of range, etc.) |
| Bulk | `500` | `{"detail": "Database error: ..."}` | DB commit failure (rare) |
