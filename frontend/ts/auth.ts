export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface OtpResponse {
  message: string;
  otp?: string;
}

export interface ApiError {
  detail?: string;
  [key: string]: unknown;
}

/**
 * Authentication Service
 * Handles JWT token management and authentication operations
 */
export class AuthService {
  public baseURL: string;
  public accessToken: string | null = null;
  public refreshToken: string | null = null;

  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.loadTokens();
  }

  /**
   * Load tokens from localStorage
   */
  private loadTokens(): void {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  /**
   * Store tokens in localStorage
   */
  public storeTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  private async parseError(response: Response, fallbackMessage: string): Promise<string> {
    try {
      const error = (await response.json()) as ApiError;
      if (error && typeof error.detail === 'string') {
        return error.detail;
      }
    } catch {
      // Ignore JSON parse errors
    }
    return fallbackMessage;
  }

  /**
   * Login with email and password (Admin)
   */
  async login(email: string, password: string): Promise<TokenResponse> {
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

    const data = (await response.json()) as TokenResponse;
    this.storeTokens(data.access_token, data.refresh_token);
    return data;
  }

  /**
   * Login with phone number and password (Jeweller)
   */
  async loginWithPhone(phoneNumber: string, password: string): Promise<TokenResponse> {
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

    const data = (await response.json()) as TokenResponse;
    this.storeTokens(data.access_token, data.refresh_token);
    return data;
  }

  /**
   * Register new user account
   */
  async register(userData: Record<string, unknown>): Promise<TokenResponse> {
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

    const data = (await response.json()) as TokenResponse;
    this.storeTokens(data.access_token, data.refresh_token);
    return data;
  }

  /**
   * Request OTP for email (Admin)
   */
  async requestOTP(email: string): Promise<OtpResponse> {
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

    return (await response.json()) as OtpResponse;
  }

  /**
   * Request OTP via WhatsApp (Jeweller)
   */
  async requestPhoneOTP(phoneNumber: string): Promise<OtpResponse> {
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

    return (await response.json()) as OtpResponse;
  }

  /**
   * Verify OTP and login (Email - Admin)
   */
  async verifyOTP(email: string, otp_code: string): Promise<TokenResponse> {
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

    const data = (await response.json()) as TokenResponse;
    this.storeTokens(data.access_token, data.refresh_token);
    return data;
  }

  /**
   * Verify WhatsApp OTP and login (Jeweller)
   */
  async verifyPhoneOTP(phoneNumber: string, otp_code: string): Promise<TokenResponse> {
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

    const data = (await response.json()) as TokenResponse;
    this.storeTokens(data.access_token, data.refresh_token);
    return data;
  }

  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<Record<string, unknown>> {
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

    return (await response.json()) as Record<string, unknown>;
  }

  /**
   * Get authentication headers with Bearer token
   */
  getAuthHeaders(): HeadersInit {
    const headers: Record<string, string> = {
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
  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  /**
   * Logout user and clear tokens
   */
  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.accessToken = null;
    this.refreshToken = null;
  }

  /**
   * Decode JWT token (without verification)
   */
  decodeToken(token: string): Record<string, unknown> | null {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload) as Record<string, unknown>;
    } catch {
      return null;
    }
  }

  /**
   * Check if token is expired
   */
  isTokenExpired(token: string): boolean {
    const decoded = this.decodeToken(token) as { exp?: number } | null;
    if (!decoded || typeof decoded.exp !== 'number') return true;

    const currentTime = Date.now() / 1000;
    return decoded.exp < currentTime;
  }
}
