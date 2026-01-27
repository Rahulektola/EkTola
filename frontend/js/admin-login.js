/**
 * Admin Login Page Logic
 * Handles admin-only authentication with role verification
 */

// Initialize AuthService
const authService = new AuthService();

// DOM Elements
let adminLoginForm, adminEmailInput, adminPasswordInput, adminPasswordToggle;
let adminLoginButton, adminFormError, successMessage, successMessageText;

// Initialize after DOM loads
document.addEventListener('DOMContentLoaded', () => {
  initializeElements();
  setupEventListeners();
  checkExistingAuth();
});

/**
 * Initialize DOM element references
 */
function initializeElements() {
  adminLoginForm = document.getElementById('adminLoginForm');
  adminEmailInput = document.getElementById('adminEmail');
  adminPasswordInput = document.getElementById('adminPassword');
  adminPasswordToggle = document.getElementById('adminPasswordToggle');
  adminLoginButton = document.getElementById('adminLoginButton');
  adminFormError = document.getElementById('adminFormError');
  successMessage = document.getElementById('successMessage');
  successMessageText = document.getElementById('successMessageText');
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
  // Admin login form
  adminLoginForm.addEventListener('submit', handleAdminLogin);
  
  // Password toggle
  adminPasswordToggle.addEventListener('click', toggleAdminPassword);
  
  // Input validation
  adminEmailInput.addEventListener('blur', () => validateEmail(adminEmailInput, 'adminEmailError'));
}

/**
 * Check if user is already authenticated as admin
 */
function checkExistingAuth() {
  if (authService.isAuthenticated()) {
    const token = authService.accessToken;
    if (!authService.isTokenExpired(token)) {
      const decoded = authService.decodeToken(token);
      
      if (decoded && decoded.is_admin) {
        // Already logged in as admin, redirect to admin dashboard
        showSuccess('Already logged in. Redirecting to admin dashboard...');
        setTimeout(() => {
          window.location.href = '/admin/dashboard.html';
        }, 1000);
      } else {
        // Logged in but not as admin, clear tokens
        authService.logout();
      }
    } else {
      // Token expired, clear it
      authService.logout();
    }
  }
}

/**
 * Handle admin login form submission
 */
async function handleAdminLogin(e) {
  e.preventDefault();
  
  const email = adminEmailInput.value.trim();
  const password = adminPasswordInput.value;
  
  // Validate inputs
  if (!validateEmail(adminEmailInput, 'adminEmailError') || !password) {
    return;
  }
  
  // Clear previous errors
  clearErrors();
  
  // Show loading state
  setLoading(adminLoginButton, true);
  
  try {
    // Attempt login
    const response = await authService.login(email, password);
    
    // Decode token to verify admin role
    const decoded = authService.decodeToken(response.access_token);
    
    // Verify this is an admin account
    if (!decoded || !decoded.is_admin) {
      showError(adminFormError, 'This account does not have admin privileges. Please use the jeweller login.');
      authService.logout();
      setLoading(adminLoginButton, false);
      return;
    }
    
    // Show success message
    showSuccess('Admin login successful! Redirecting to admin dashboard...');
    
    // Redirect to admin dashboard after short delay
    setTimeout(() => {
      window.location.href = '/admin/dashboard.html';
    }, 1500);
    
  } catch (error) {
    // Show error message
    showError(adminFormError, error.message || 'Admin login failed. Please check your credentials.');
    setLoading(adminLoginButton, false);
  }
}

/**
 * Toggle password visibility
 */
function toggleAdminPassword() {
  const type = adminPasswordInput.type === 'password' ? 'text' : 'password';
  adminPasswordInput.type = type;
  
  // Update icon
  const eyeIcon = document.getElementById('adminEyeIcon');
  if (type === 'text') {
    eyeIcon.innerHTML = `
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
      <line x1="1" y1="1" x2="23" y2="23"></line>
    `;
  } else {
    eyeIcon.innerHTML = `
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
      <circle cx="12" cy="12" r="3"></circle>
    `;
  }
}

/**
 * Validate email format
 */
function validateEmail(inputElement, errorId) {
  const email = inputElement.value.trim();
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const errorElement = document.getElementById(errorId);
  
  if (!email) {
    showError(errorElement, 'Email is required.');
    inputElement.classList.add('error');
    return false;
  }
  
  if (!emailRegex.test(email)) {
    showError(errorElement, 'Please enter a valid email address.');
    inputElement.classList.add('error');
    return false;
  }
  
  inputElement.classList.remove('error');
  if (errorElement) {
    errorElement.textContent = '';
  }
  return true;
}

/**
 * Show error message
 */
function showError(element, message) {
  if (element) {
    element.textContent = message;
    element.classList.add('visible');
  }
}

/**
 * Clear all error messages
 */
function clearErrors() {
  const errorElements = document.querySelectorAll('.form-error, .form-error-message');
  errorElements.forEach(el => {
    el.textContent = '';
    el.classList.remove('visible');
  });
  
  const inputs = document.querySelectorAll('.form-input');
  inputs.forEach(input => input.classList.remove('error'));
}

/**
 * Set loading state for button
 */
function setLoading(button, isLoading) {
  if (isLoading) {
    button.classList.add('loading');
    button.disabled = true;
  } else {
    button.classList.remove('loading');
    button.disabled = false;
  }
}

/**
 * Show success message
 */
function showSuccess(message) {
  successMessageText.textContent = message;
  successMessage.classList.add('visible');
  
  // Auto-hide after 3 seconds
  setTimeout(() => {
    successMessage.classList.remove('visible');
  }, 3000);
}

/**
 * Handle form input on Enter key
 */
document.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
    const activeForm = document.getElementById('adminLoginForm');
    if (activeForm) {
      const submitButton = adminLoginButton;
      if (submitButton && !submitButton.disabled) {
        e.preventDefault();
        submitButton.click();
      }
    }
  }
});
