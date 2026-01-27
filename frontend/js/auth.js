/**
 * Authentication Service
 * Handles JWT token management and authentication operations
 */
class AuthService {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.accessToken = null;
    this.refreshToken = null;
    
    // Load tokens from localStorage on initialization
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

  /**
   * Login with email and password
   * @param {string} email - User email
   * @param {string} password - User password
   * @returns {Promise<Object>} Token response
   */
  async login(email, password) {
    try {
      const response = await fetch(`${this.baseURL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      this.storeTokens(data.access_token, data.refresh_token);
      
      return data;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Register new user account
   * @param {Object} userData - User registration data
   * @returns {Promise<Object>} Token response
   */
  async register(userData) {
    try {
      const response = await fetch(`${this.baseURL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Registration failed');
      }

      const data = await response.json();
      this.storeTokens(data.access_token, data.refresh_token);
      
      return data;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Request OTP for email
   * @param {string} email - User email
   * @returns {Promise<Object>} Response message
   */
  async requestOTP(email) {
    try {
      const response = await fetch(`${this.baseURL}/auth/request-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'OTP request failed');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  }

  /**
   * Verify OTP and login
   * @param {string} email - User email
   * @param {string} otp - OTP code
   * @returns {Promise<Object>} Token response
   */
  async verifyOTP(email, otp) {
    try {
      const response = await fetch(`${this.baseURL}/auth/verify-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, otp }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'OTP verification failed');
      }

      const data = await response.json();
      this.storeTokens(data.access_token, data.refresh_token);
      
      return data;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get current user profile
   * @returns {Promise<Object>} User profile
   */
  async getCurrentUser() {
    try {
      const response = await fetch(`${this.baseURL}/auth/me`, {
        method: 'GET',
        headers: this.getAuthHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          this.logout();
          throw new Error('Session expired. Please login again.');
        }
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch user profile');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get authentication headers with Bearer token
   * @returns {Object} Headers object
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
   * @returns {boolean} Authentication status
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
   * @param {string} token - JWT token
   * @returns {Object} Decoded payload
   */
  decodeToken(token) {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      return null;
    }
  }

  /**
   * Check if token is expired
   * @param {string} token - JWT token
   * @returns {boolean} Expiration status
   */
  isTokenExpired(token) {
    const decoded = this.decodeToken(token);
    if (!decoded || !decoded.exp) return true;
    
    const currentTime = Date.now() / 1000;
    return decoded.exp < currentTime;
  }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AuthService;
}
