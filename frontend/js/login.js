/**
 * Login Page Logic
 * Handles form interactions and authentication flows
 */

// Initialize AuthService
const authService = new AuthService();

// DOM Elements
let passwordLoginForm, otpRequestForm, otpVerifyForm;
let phoneNumberInput, passwordInput, passwordToggle, loginButton, loginLoader;
let otpPhoneInput, otpCode, requestOtpButton, verifyOtpButton, resendOtpButton;
let formError, successMessage, successMessageText;
let tabButtons, tabContents;

// State
let currentOtpPhone = '';

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
  // Forms
  passwordLoginForm = document.getElementById('passwordLoginForm');
  otpRequestForm = document.getElementById('otpRequestForm');
  otpVerifyForm = document.getElementById('otpVerifyForm');
  
  // Password login inputs
  phoneNumberInput = document.getElementById('phoneNumber');
  passwordInput = document.getElementById('password');
  passwordToggle = document.getElementById('passwordToggle');
  loginButton = document.getElementById('loginButton');
  loginLoader = document.getElementById('loginLoader');
  
  // OTP inputs
  otpPhoneInput = document.getElementById('otpPhone');
  otpCode = document.getElementById('otpCode');
  requestOtpButton = document.getElementById('requestOtpButton');
  verifyOtpButton = document.getElementById('verifyOtpButton');
  resendOtpButton = document.getElementById('resendOtpButton');
  
  // UI elements
  formError = document.getElementById('formError');
  successMessage = document.getElementById('successMessage');
  successMessageText = document.getElementById('successMessageText');
  
  // Tabs
  tabButtons = document.querySelectorAll('.tab-button');
  tabContents = document.querySelectorAll('.tab-content');
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
  // Tab navigation
  tabButtons.forEach(button => {
    button.addEventListener('click', () => handleTabChange(button.dataset.tab));
  });
  
  // Password login form
  passwordLoginForm.addEventListener('submit', handlePasswordLogin);
  
  // Password toggle
  passwordToggle.addEventListener('click', togglePasswordVisibility);
  
  // OTP request form
  otpRequestForm.addEventListener('submit', handleOtpRequest);
  
  // OTP verify form
  otpVerifyForm.addEventListener('submit', handleOtpVerify);
  
  // Resend OTP button
  resendOtpButton.addEventListener('click', handleResendOtp);
  
  // Change email button
  document.getElementById('changePhoneButton').addEventListener('click', () => {
    otpRequestForm.classList.add('active');
    otpVerifyForm.classList.remove('active');
    otpCode.value = '';
  });
  
  // Forgot password link
  document.getElementById('forgotPasswordLink').addEventListener('click', (e) => {
    e.preventDefault();
    handleTabChange('otp');
    if (phoneNumberInput.value) {
      otpPhoneInput.value = phoneNumberInput.value;
    }
  });
  
  // Input validation
  phoneNumberInput.addEventListener('blur', () => validatePhone(phoneNumberInput));
  otpPhoneInput.addEventListener('blur', () => validatePhone(otpPhoneInput));
  
  // OTP input formatting
  otpCode.addEventListener('input', (e) => {
    e.target.value = e.target.value.replace(/\D/g, '').slice(0, 6);
  });
}

/**
 * Check if user is already authenticated
 */
function checkExistingAuth() {
  if (authService.isAuthenticated()) {
    const token = authService.accessToken;
    if (!authService.isTokenExpired(token)) {
      // User is already logged in, redirect to dashboard
      showSuccess('Already logged in. Redirecting...');
      setTimeout(() => {
        window.location.href = '/dashboard.html';
      }, 1000);
    } else {
      // Token expired, clear it
      authService.logout();
    }
  }
}

/**
 * Handle tab switching
 */
function handleTabChange(tabName) {
  // Update tab buttons
  tabButtons.forEach(button => {
    if (button.dataset.tab === tabName) {
      button.classList.add('active');
    } else {
      button.classList.remove('active');
    }
  });
  
  // Update tab content
  tabContents.forEach(content => {
    if (content.dataset.content === tabName) {
      content.classList.add('active');
    } else {
      content.classList.remove('active');
    }
  });
  
  // Clear errors
  clearErrors();
}

/**
 * Handle password login form submission
 */
async function handlePasswordLogin(e) {
  e.preventDefault();
  
  const phoneNumber = phoneNumberInput.value.trim();
  const password = passwordInput.value;
  
  // Validate inputs
  if (!validatePhone(phoneNumberInput) || !password) {
    return;
  }
  
  // Clear previous errors
  clearErrors();
  
  // Show loading state
  setLoading(loginButton, true);
  
  try {
    // Attempt login with phone
    const response = await authService.loginWithPhone(phoneNumber, password);
    
    // Decode token to check user role
    const decoded = authService.decodeToken(response.access_token);
    
    // Role-based redirect
    if (decoded && decoded.is_admin) {
      showSuccess('Login successful! Redirecting to admin dashboard...');
      setTimeout(() => {
        window.location.href = '/admin/dashboard.html';
      }, 1500);
    } else {
      showSuccess('Login successful! Redirecting to dashboard...');
      setTimeout(() => {
        window.location.href = '/dashboard.html';
      }, 1500);
    }
    
  } catch (error) {
    // Show error message
    showError(formError, error.message || 'Login failed. Please check your credentials.');
    setLoading(loginButton, false);
  }
}

/**
 * Handle OTP request
 */
async function handleOtpRequest(e) {
  e.preventDefault();
  
  const phoneNumber = otpPhoneInput.value.trim();
  
  // Validate phone
  if (!validatePhone(otpPhoneInput)) {
    return;
  }
  
  // Clear previous errors
  clearErrors();
  
  // Show loading state
  setLoading(requestOtpButton, true);
  
  try {
    // Request OTP via WhatsApp
    const response = await authService.requestPhoneOTP(phoneNumber);
    
    // Store phone for verification step
    currentOtpPhone = phoneNumber;
    document.getElementById('otpPhoneDisplay').textContent = phoneNumber;
    
    // Switch to verification form
    otpRequestForm.classList.remove('active');
    otpVerifyForm.classList.add('active');
    
    // Focus on OTP input
    setTimeout(() => otpCode.focus(), 100);
    
    // Show OTP in console for development (backend sends it in dev mode)
    if (response.otp) {
      console.log('Development OTP:', response.otp);
    }
    
  } catch (error) {
    showError(document.getElementById('otpRequestError'), error.message || 'Failed to send OTP.');
    setLoading(requestOtpButton, false);
  } finally {
    setLoading(requestOtpButton, false);
  }
}

/**
 * Handle OTP verification
 */
async function handleOtpVerify(e) {
  e.preventDefault();
  
  const otp = otpCode.value.trim();
  
  // Validate OTP
  if (otp.length !== 6) {
    showError(document.getElementById('otpCodeError'), 'Please enter a 6-digit OTP code.');
    return;
  }
  
  // Clear previous errors
  clearErrors();
  
  // Show loading state
  setLoading(verifyOtpButton, true);
  
  try {
    // Verify OTP and login with phone
    const response = await authService.verifyPhoneOTP(currentOtpPhone, otp);
    
    // Decode token to check user role
    const decoded = authService.decodeToken(response.access_token);
    
    // Role-based redirect
    if (decoded && decoded.is_admin) {
      showSuccess('Login successful! Redirecting to admin dashboard...');
      setTimeout(() => {
        window.location.href = '/admin/dashboard.html';
      }, 1500);
    } else {
      showSuccess('Login successful! Redirecting to dashboard...');
      setTimeout(() => {
        window.location.href = '/dashboard.html';
      }, 1500);
    }
    
  } catch (error) {
    showError(document.getElementById('otpVerifyError'), error.message || 'Invalid OTP. Please try again.');
    setLoading(verifyOtpButton, false);
  }
}

/**
 * Handle resend OTP
 */
async function handleResendOtp() {
  clearErrors();
  setLoading(resendOtpButton, true);
  
  try {
    await authService.requestPhoneOTP(currentOtpPhone);
    
    // Show temporary success message
    const otpInfo = document.querySelector('.otp-info p');
    const originalText = otpInfo.innerHTML;
    otpInfo.innerHTML = '<strong style="color: var(--success-color);">OTP resent successfully!</strong>';
    
    setTimeout(() => {
      otpInfo.innerHTML = originalText;
    }, 3000);
    
  } catch (error) {
    showError(document.getElementById('otpVerifyError'), error.message || 'Failed to resend OTP.');
  } finally {
    setLoading(resendOtpButton, false);
  }
}

/**
 * Toggle password visibility
 */
function togglePasswordVisibility() {
  const type = passwordInput.type === 'password' ? 'text' : 'password';
  passwordInput.type = type;
  
  // Update icon (simple toggle, you can enhance with different SVGs)
  const eyeIcon = document.getElementById('eyeIcon');
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
function validateEmail(inputElement) {
  const email = inputElement.value.trim();
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const errorElement = document.getElementById(inputElement.id + 'Error');
  
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
 * Normalize phone number to E.164 format
 */
function normalizePhoneNumber(phone) {
  // Remove all spaces, dashes, and parentheses
  let cleaned = phone.replace(/[\s\-\(\)]/g, '');
  
  // If it starts with +91, keep it as is
  if (cleaned.startsWith('+91')) {
    return cleaned;
  }
  
  // If it starts with 91 (without +), add +
  if (cleaned.startsWith('91') && cleaned.length === 12) {
    return '+' + cleaned;
  }
  
  // If it's just 10 digits, assume it's Indian number and add +91
  if (/^[6-9]\d{9}$/.test(cleaned)) {
    return '+91' + cleaned;
  }
  
  // Otherwise return as is
  return cleaned;
}

/**
 * Validate phone number (accepts multiple formats)
 */
function validatePhone(inputElement) {
  const phone = inputElement.value.trim();
  const errorElement = document.getElementById(inputElement.id + 'Error');
  
  if (!phone) {
    showError(errorElement, 'Phone number is required.');
    inputElement.classList.add('error');
    return false;
  }
  
  // Normalize the phone number
  const normalized = normalizePhoneNumber(phone);
  
  // Validate normalized format (E.164)
  const phoneRegex = /^\+[1-9]\d{1,14}$/;
  
  if (!phoneRegex.test(normalized)) {
    showError(errorElement, 'Please enter a valid 10-digit mobile number.');
    inputElement.classList.add('error');
    return false;
  }
  
  // Update input with normalized value
  inputElement.value = normalized;
  
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
    const activeForm = document.querySelector('.auth-form.active form, .otp-step.active');
    if (activeForm) {
      const submitButton = activeForm.querySelector('button[type="submit"]');
      if (submitButton && !submitButton.disabled) {
        e.preventDefault();
        submitButton.click();
      }
    }
  }
});
