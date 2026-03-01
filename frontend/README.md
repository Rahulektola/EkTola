# ekTola Frontend

Modern, mobile-first Progressive Web App (PWA) for the ekTola WhatsApp Campaign Management System.

## 🚀 Quick Start

### Prerequisites
- A web server (Python, Node.js, or any HTTP server)
- Backend API running at `http://localhost:8000` (see main README.md)

### Running the Frontend

#### Option 1: Python HTTP Server
```bash
cd frontend
python -m http.server 3000
```

#### Option 2: Node.js HTTP Server
```bash
npm install -g http-server
cd frontend
http-server -p 3000
```

#### Option 3: PHP Built-in Server
```bash
cd frontend
php -S localhost:3000
```

Then open your browser to: **http://localhost:3000**

## 📁 Project Structure

```
frontend/
├── index.html              # Login page
├── offline.html            # Offline fallback page
├── manifest.json           # PWA manifest
├── service-worker.js       # Service worker for offline support
├── css/
│   └── style.css          # Main stylesheet (mobile-first)
└── js/
    ├── auth.js            # AuthService class
    └── login.js           # Login page logic
```

## 🔑 Features

### Authentication
- **Password Login**: Email + password authentication
- **OTP Login**: One-Time Password via email
- **Remember Me**: Optional persistent session
- **Forgot Password**: OTP-based password recovery flow
- **Auto-redirect**: Checks for existing valid tokens

### Security
- JWT token management (access + refresh tokens)
- Secure localStorage token storage
- Bearer token authentication
- Token expiration detection
- Auto-logout on 401 responses

### Progressive Web App (PWA)
- ✅ Mobile-first responsive design
- ✅ Touch-friendly UI (48x48px minimum targets)
- ✅ Offline support via Service Worker
- ✅ "Add to Home Screen" capability
- ✅ Manifest for native app experience
- ✅ Optimized for low-end devices
- ✅ Online/offline status indicator

### User Experience
- Real-time form validation
- Password visibility toggle
- Loading states and spinners
- Error message display
- Success notifications
- Tab navigation (Password/OTP)
- Keyboard shortcuts (Enter to submit)

## 🔧 Configuration

### API Base URL

The default API base URL is `http://localhost:8000`. To change it:

Edit `frontend/js/auth.js`:
```javascript
const authService = new AuthService('https://api.ektola.com');
```

Or in `frontend/js/login.js`:
```javascript
const authService = new AuthService('https://your-api-url.com');
```

### Environment Variables (Optional)

You can create a `config.js` file:
```javascript
const CONFIG = {
  API_BASE_URL: 'http://localhost:8000',
  ENABLE_DEBUG: true
};
```

## 🎨 Customization

### Theming

Edit CSS variables in `frontend/css/style.css`:
```css
:root {
  --primary-color: #6366f1;
  --primary-hover: #4f46e5;
  --success-color: #10b981;
  --error-color: #ef4444;
  /* ... more variables ... */
}
```

### Dark Mode

The app includes automatic dark mode support based on system preference. You can customize colors in the `@media (prefers-color-scheme: dark)` section.

## 📱 Testing

### Desktop Testing
1. Open http://localhost:3000
2. Open DevTools (F12)
3. Test both Password and OTP login flows

### Mobile Testing

#### Using Chrome DevTools:
1. Open DevTools (F12)
2. Click "Toggle device toolbar" (Ctrl+Shift+M)
3. Select a mobile device (e.g., iPhone 12, Pixel 5)
4. Test touch interactions

#### On Real Device:
1. Ensure your device is on the same network
2. Find your computer's IP address:
   - Windows: `ipconfig`
   - Mac/Linux: `ifconfig`
3. Open `http://YOUR_IP:3000` on your mobile browser
4. Test PWA installation: "Add to Home Screen"

### PWA Testing
1. Open Chrome DevTools → Application tab
2. Check "Service Workers" (should show registered)
3. Check "Manifest" (should show app details)
4. Test offline mode:
   - Go to Network tab
   - Select "Offline"
   - Reload page → should show offline page

## 🔐 API Integration

### Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | POST | Email + password login |
| `/auth/register` | POST | New user registration |
| `/auth/request-otp` | POST | Request OTP code |
| `/auth/verify-otp` | POST | Verify OTP and login |
| `/auth/me` | GET | Get current user profile |

### Request Examples

**Password Login:**
```javascript
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secretpassword"
}
```

**Response:**
```javascript
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

## 🐛 Troubleshooting

### CORS Issues
If you see CORS errors in the console:
1. Ensure backend is running
2. Backend should allow frontend origin in CORS settings
3. Check `app/main.py` for CORS middleware configuration

### Service Worker Not Registering
1. Serve over HTTPS or localhost (HTTP)
2. Check browser console for errors
3. Clear browser cache and reload
4. Verify `service-worker.js` is accessible

### Login Not Working
1. Verify backend is running at `http://localhost:8000`
2. Test backend endpoint: `curl http://localhost:8000/auth/login`
3. Check browser console for error messages
4. Verify email/password credentials

### Offline Mode Not Working
1. Register Service Worker first (visit page online)
2. Check DevTools → Application → Service Workers
3. Toggle offline mode in Network tab
4. Reload page

## 📝 Development Notes

### Adding New Pages
1. Create HTML file (e.g., `dashboard.html`)
2. Link CSS: `<link rel="stylesheet" href="/css/style.css">`
3. Include auth check:
   ```javascript
   if (!authService.isAuthenticated()) {
     window.location.href = '/index.html';
   }
   ```
4. Add to Service Worker cache in `PRECACHE_URLS`

### Making Authenticated API Calls
```javascript
const response = await fetch('http://localhost:8000/api/campaigns', {
  method: 'GET',
  headers: authService.getAuthHeaders()
});
```

### Handling Token Expiration
```javascript
try {
  const response = await fetch(url, options);
  if (response.status === 401) {
    authService.logout();
    window.location.href = '/index.html';
  }
} catch (error) {
  // Handle error
}
```

## 🚦 Browser Support

- ✅ Chrome 90+ (Desktop & Mobile)
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ✅ Samsung Internet 14+
- ✅ Opera 76+

## 📦 Production Deployment

### Build Optimizations
1. Minify CSS and JavaScript
2. Optimize images (WebP format)
3. Generate PWA icons (72x72 to 512x512)
4. Enable HTTPS (required for Service Workers)
5. Configure CDN for static assets
6. Set up proper caching headers

### Environment Setup
1. Update API base URL to production
2. Set `ENABLE_DEBUG` to false
3. Add analytics tracking (optional)
4. Configure error reporting (Sentry, etc.)

## 📄 License

This frontend is part of the ekTola project.

## 🤝 Contributing

1. Follow mobile-first design principles
2. Maintain 48x48px minimum touch targets
3. Test on real mobile devices
4. Ensure accessibility (WCAG 2.1 AA)
5. Keep bundle size minimal

## 📞 Support

For issues or questions:
- Check the main project README.md
- Review FRONTEND_CONTRACT.md for API documentation
- Open an issue on the project repository

---

**Built with ❤️ for Jewellers**
