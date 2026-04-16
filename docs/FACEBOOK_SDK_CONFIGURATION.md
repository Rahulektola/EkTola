# Facebook SDK Configuration Guide

## Overview
The Meta Embedded Signup URLs and App IDs are now configurable via environment variables, making it easy to update them when Meta changes their SDK or API versions.

## Environment Variables

Add these to your `.env` file:

```bash
# WhatsApp Embedded Signup (Jeweller Accounts)
WHATSAPP_API_VERSION=v25.0
WHATSAPP_APP_ID=1607280397050756   # Client id (from Meta App Dashboard)
WHATSAPP_APP_SECRET=7a744336444a9aede1bf9952d343db2d   # Client secret
FACEBOOK_CONFIG_ID=1271517688508366  # Embedded Signup Config ID
FACEBOOK_SDK_URL=https://connect.facebook.net/en_US/sdk.js  # Facebook SDK URL
```

## What Can Change

### 1. Facebook SDK URL (`FACEBOOK_SDK_URL`)
**Current:** `https://connect.facebook.net/en_US/sdk.js`

**When to update:**
- Meta releases a new SDK version
- Meta changes the CDN URL
- You want to use a different locale (e.g., `en_GB`, `es_ES`)

**Examples:**
```bash
# Different locale
FACEBOOK_SDK_URL=https://connect.facebook.net/es_ES/sdk.js

# Debug version (for development)
FACEBOOK_SDK_URL=https://connect.facebook.net/en_US/sdk/debug.js
```

### 2. WhatsApp API Version (`WHATSAPP_API_VERSION`)
**Current:** `v25.0`

**When to update:**
- Meta deprecates the current API version
- You want to use new features from a newer version

**Examples:**
```bash
WHATSAPP_API_VERSION=v26.0  # When Meta releases v26
WHATSAPP_API_VERSION=v27.0  # Future versions
```

### 3. Facebook Config ID (`FACEBOOK_CONFIG_ID`)
**Current:** `1271517688508366`

**When to update:**
- You create a new Embedded Signup configuration in Meta Dashboard
- You want to change the permissions or settings

**Where to find:**
Meta Developer Dashboard → Your App → WhatsApp → Configuration → Embedded Signup

## How It Works

### Backend Flow
1. Frontend requests config from `/api/auth/whatsapp/config`
2. Backend returns:
   ```json
   {
     "appId": "1607280397050756",
     "configId": "1271517688508366",
     "sdkUrl": "https://connect.facebook.net/en_US/sdk.js",
     "apiVersion": "v25.0",
     "redirectUri": "http://localhost:8000/auth/whatsapp/callback",
     "state": "eyJ0eXAiOiJKV1QiLCJhbGc..."
   }
   ```
3. Frontend dynamically loads the SDK and initializes FB with these values

### Frontend Implementation
File: `frontend/dashboard.html`

The script now:
- Fetches config from backend
- Dynamically loads the SDK script
- Initializes FB.init() with correct values
- Falls back to defaults if config fetch fails

## Files Modified

1. **Environment Configuration**
   - `new.env` - Added `FACEBOOK_SDK_URL`

2. **Backend**
   - `app/config.py` - Added `FACEBOOK_SDK_URL` setting
   - `app/schemas/auth.py` - Added `sdkUrl` and `apiVersion` to response
   - `app/services/whatsapp_auth_routes.py` - Returns SDK URL in config endpoint

3. **Frontend**
   - `frontend/dashboard.html` - Dynamic SDK loading and initialization

## Testing

After making changes:

1. **Update `.env` file** with new values
2. **Restart backend server** to load new config
3. **Clear browser cache** and reload frontend
4. **Test WhatsApp connection** on dashboard

## Where to Find Values on Meta Dashboard

### System User Token
1. Go to [Meta Business Manager](https://business.facebook.com/)
2. Business Settings → Users → System Users
3. Select/Create system user → Generate New Token
4. Select app and permissions:
   - `whatsapp_business_management`
   - `whatsapp_business_messaging`
5. Copy the token

### App ID & App Secret
1. Go to [Meta Developers](https://developers.facebook.com/)
2. Select your app
3. Settings → Basic
4. Copy "App ID" and "App Secret"

### Config ID
1. Meta Developers → Your App
2. WhatsApp → Configuration
3. Embedded Signup section
4. Copy the Configuration ID

### API Version
Check [WhatsApp Business Platform Changelog](https://developers.facebook.com/docs/whatsapp/business-platform/changelog) for latest version.

## Troubleshooting

### SDK Not Loading
- Check `FACEBOOK_SDK_URL` is reachable
- Verify no CORS issues in browser console
- Try the debug SDK: `https://connect.facebook.net/en_US/sdk/debug.js`

### Wrong App Initializing
- Clear browser cache
- Verify `WHATSAPP_APP_ID` matches your Meta app
- Check browser console for FB.init() logs

### OAuth Flow Fails
- Verify `FACEBOOK_CONFIG_ID` is correct
- Check `WHATSAPP_API_VERSION` is supported
- Ensure callback URL is whitelisted in Meta app settings
