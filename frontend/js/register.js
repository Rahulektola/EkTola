/**
 * Jeweller Registration Page Logic
 */

// Initialize AuthService
const authService = new AuthService();

// DOM Elements
let registerForm, businessNameInput, phoneNumberInput, registerEmailInput;
let registerPasswordInput, confirmPasswordInput;
let registerPasswordToggle, confirmPasswordToggle;
let registerButton, registerFormError, successMessage, successMessageText;

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
  registerForm = document.getElementById('registerForm');
  businessNameInput = document.getElementById('businessName');
  phoneNumberInput = document.getElementById('phoneNumber');
  registerEmailInput = document.getElementById('registerEmail');
  registerPasswordInput = document.getElementById('registerPassword');
  confirmPasswordInput = document.getElementById('confirmPassword');
  registerPasswordToggle = document.getElementById('registerPasswordToggle');
  confirmPasswordToggle = document.getElementById('confirmPasswordToggle');
  registerButton = document.getElementById('registerButton');
  registerFormError = document.getElementById('registerFormError');
  successMessage = document.getElementById('successMessage');
  successMessageText = document.getElementById('successMessageText');
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
  // Registration form
  registerForm.addEventListener('submit', handleRegistration);
  
  // Password toggles
  registerPasswordToggle.addEventListener('click', () => togglePassword('registerPassword', 'registerEyeIcon'));
  confirmPasswordToggle.addEventListener('click', () => togglePassword('confirmPassword', 'confirmEyeIcon'));
  
  // Input validation
  businessNameInput.addEventListener('blur', () => validateRequired(businessNameInput, 'businessNameError', 'Business name'));
  phoneNumberInput.addEventListener('blur', () => validatePhone(phoneNumberInput));
  registerEmailInput.addEventListener('blur', () => validateEmail(registerEmailInput, 'registerEmailError'));
  registerPasswordInput.addEventListener('blur', () => validatePassword(registerPasswordInput));
  confirmPasswordInput.addEventListener('blur', () => validatePasswordMatch());
}

/**
 * Check if user is already authenticated
 */
function checkExistingAuth() {
  if (authService.isAuthenticated()) {
    const token = authService.accessToken;
    if (!authService.isTokenExpired(token)) {
      // Already logged in, redirect to dashboard
      window.location.href = '/dashboard.html';
    } else {
      authService.logout();
    }
  }
}

/**
 * Handle registration form submission
 */
async function handleRegistration(e) {
  e.preventDefault();
  
  const businessName = businessNameInput.value.trim();
  const phoneNumber = phoneNumberInput.value.trim();
  const email = registerEmailInput.value.trim();
  const password = registerPasswordInput.value;
  const confirmPassword = confirmPasswordInput.value;
  
  // Validate all inputs
  let isValid = true;
  isValid = validateRequired(businessNameInput, 'businessNameError', 'Business name') && isValid;
  isValid = validatePhone(phoneNumberInput) && isValid;
  isValid = validateEmail(registerEmailInput, 'registerEmailError') && isValid;
  isValid = validatePassword(registerPasswordInput) && isValid;
  isValid = validatePasswordMatch() && isValid;
  
  if (!isValid) {
    return;
  }
  
  // Clear previous errors
  clearErrors();
  
  // Show loading state
  setLoading(registerButton, true);
  
  try {
    // Attempt registration
    const response = await authService.register({
      business_name: businessName,
      phone_number: phoneNumber,
      email: email,
      password: password
    });
    
    // Show success message
    showSuccess('Registration successful! Your account is pending admin approval. Redirecting to dashboard...');
    
    // Redirect to dashboard after short delay
    setTimeout(() => {
      window.location.href = '/dashboard.html';
    }, 2500);
    
  } catch (error) {
    // Show error message
    showError(registerFormError, error.message || 'Registration failed. Please try again.');
    setLoading(registerButton, false);
  }
}

/**
 * Validate required field
 */
function validateRequired(inputElement, errorId, fieldName) {
  const value = inputElement.value.trim();
  const errorElement = document.getElementById(errorId);
  
  if (!value) {
    showError(errorElement, `${fieldName} is required.`);
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
 * Validate phone number
 */
function validatePhone(inputElement) {
  const phone = inputElement.value.trim();
  const phoneRegex = /^[+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}$/;
  const errorElement = document.getElementById('phoneNumberError');
  
  if (!phone) {
    showError(errorElement, 'Phone number is required.');
    inputElement.classList.add('error');
    return false;
  }
  
  if (!phoneRegex.test(phone)) {
    showError(errorElement, 'Please enter a valid phone number.');
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
 * Validate password strength
 */
function validatePassword(inputElement) {
  const password = inputElement.value;
  const errorElement = document.getElementById('registerPasswordError');
  
  if (!password) {
    showError(errorElement, 'Password is required.');
    inputElement.classList.add('error');
    return false;
  }
  
  if (password.length < 8) {
    showError(errorElement, 'Password must be at least 8 characters long.');
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
 * Validate password match
 */
function validatePasswordMatch() {
  const password = registerPasswordInput.value;
  const confirmPassword = confirmPasswordInput.value;
  const errorElement = document.getElementById('confirmPasswordError');
  
  if (!confirmPassword) {
    showError(errorElement, 'Please confirm your password.');
    confirmPasswordInput.classList.add('error');
    return false;
  }
  
  if (password !== confirmPassword) {
    showError(errorElement, 'Passwords do not match.');
    confirmPasswordInput.classList.add('error');
    return false;
  }
  
  confirmPasswordInput.classList.remove('error');
  if (errorElement) {
    errorElement.textContent = '';
  }
  return true;
}

/**
 * Toggle password visibility
 */
function togglePassword(inputId, iconId) {
  const input = document.getElementById(inputId);
  const icon = document.getElementById(iconId);
  const type = input.type === 'password' ? 'text' : 'password';
  input.type = type;
  
  if (type === 'text') {
    icon.innerHTML = `
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
      <line x1="1" y1="1" x2="23" y2="23"></line>
    `;
  } else {
    icon.innerHTML = `
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
      <circle cx="12" cy="12" r="3"></circle>
    `;
  }
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
  
  // Auto-hide after 5 seconds
  setTimeout(() => {
    successMessage.classList.remove('visible');
  }, 5000);
}
