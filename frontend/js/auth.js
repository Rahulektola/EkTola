/**
 * Authentication Service
 * Handles JWT token management and authentication operations
 */
export class AuthService {
    constructor(baseURL = 'http://localhost:8000') {
        this.accessToken = null;
        this.refreshToken = null;
        this.baseURL = baseURL;
        this.loadTokens();
    }
    /**
     * Load tokens from localStorage
     */
    loadTokens() {
        this.accessToken = localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }
    /**
     * Store tokens in localStorage
     */
    storeTokens(accessToken, refreshToken) {
        this.accessToken = accessToken;
        this.refreshToken = refreshToken;
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
    }
    async parseError(response, fallbackMessage) {
        try {
            const error = (await response.json());
            if (error && typeof error.detail === 'string') {
                return error.detail;
            }
        }
        catch {
            // Ignore JSON parse errors
        }
        return fallbackMessage;
    }
    /**
     * Login with email and password (Admin)
     */
    async login(email, password) {
        const response = await fetch(`${this.baseURL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
        });
        if (!response.ok) {
            const message = await this.parseError(response, 'Login failed');
            throw new Error(message);
        }
        const data = (await response.json());
        this.storeTokens(data.access_token, data.refresh_token);
        return data;
    }
    /**
     * Login with phone number and password (Jeweller)
     */
    async loginWithPhone(phoneNumber, password) {
        const response = await fetch(`${this.baseURL}/auth/login/phone`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ phone_number: phoneNumber, password }),
        });
        if (!response.ok) {
            const message = await this.parseError(response, 'Login failed');
            throw new Error(message);
        }
        const data = (await response.json());
        this.storeTokens(data.access_token, data.refresh_token);
        return data;
    }
    /**
     * Register new user account
     */
    async register(userData) {
        const response = await fetch(`${this.baseURL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData),
        });
        if (!response.ok) {
            const message = await this.parseError(response, 'Registration failed');
            throw new Error(message);
        }
        const data = (await response.json());
        this.storeTokens(data.access_token, data.refresh_token);
        return data;
    }
    /**
     * Request OTP for email (Admin)
     */
    async requestOTP(email) {
        const response = await fetch(`${this.baseURL}/auth/otp/request`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email }),
        });
        if (!response.ok) {
            const message = await this.parseError(response, 'OTP request failed');
            throw new Error(message);
        }
        return (await response.json());
    }
    /**
     * Request OTP via WhatsApp (Jeweller)
     */
    async requestPhoneOTP(phoneNumber) {
        const response = await fetch(`${this.baseURL}/auth/otp/request/phone`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ phone_number: phoneNumber }),
        });
        if (!response.ok) {
            const message = await this.parseError(response, 'OTP request failed');
            throw new Error(message);
        }
        return (await response.json());
    }
    /**
     * Verify OTP and login (Email - Admin)
     */
    async verifyOTP(email, otp_code) {
        const response = await fetch(`${this.baseURL}/auth/otp/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, otp_code }),
        });
        if (!response.ok) {
            const message = await this.parseError(response, 'OTP verification failed');
            throw new Error(message);
        }
        const data = (await response.json());
        this.storeTokens(data.access_token, data.refresh_token);
        return data;
    }
    /**
     * Verify WhatsApp OTP and login (Jeweller)
     */
    async verifyPhoneOTP(phoneNumber, otp_code) {
        const response = await fetch(`${this.baseURL}/auth/otp/verify/phone`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ phone_number: phoneNumber, otp_code }),
        });
        if (!response.ok) {
            const message = await this.parseError(response, 'OTP verification failed');
            throw new Error(message);
        }
        const data = (await response.json());
        this.storeTokens(data.access_token, data.refresh_token);
        return data;
    }
    /**
     * Get current user profile
     */
    async getCurrentUser() {
        const response = await fetch(`${this.baseURL}/auth/me`, {
            method: 'GET',
            headers: this.getAuthHeaders(),
        });
        if (!response.ok) {
            if (response.status === 401) {
                this.logout();
                throw new Error('Session expired. Please login again.');
            }
            const message = await this.parseError(response, 'Failed to fetch user profile');
            throw new Error(message);
        }
        return (await response.json());
    }
    /**
     * Get authentication headers with Bearer token
     */
    getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        if (this.accessToken) {
            headers['Authorization'] = `Bearer ${this.accessToken}`;
        }
        return headers;
    }
    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.accessToken;
    }
    /**
     * Logout user and clear tokens
     */
    logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        this.accessToken = null;
        this.refreshToken = null;
    }
    /**
     * Decode JWT token (without verification)
     */
    decodeToken(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64)
                .split('')
                .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join(''));
            return JSON.parse(jsonPayload);
        }
        catch {
            return null;
        }
    }
    /**
     * Check if token is expired
     */
    isTokenExpired(token) {
        const decoded = this.decodeToken(token);
        if (!decoded || typeof decoded.exp !== 'number')
            return true;
        const currentTime = Date.now() / 1000;
        return decoded.exp < currentTime;
    }
}
// Make AuthService globally available
window.AuthService = AuthService;
window.authService = new AuthService();
//# sourceMappingURL=auth.js.map