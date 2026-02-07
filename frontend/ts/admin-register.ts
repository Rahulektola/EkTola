import { AuthService } from './auth.js';

/**
 * Admin Registration Page Logic
 * Note: This requires backend endpoint /auth/register-admin which may not exist yet
 */

const authService = new AuthService();

let adminRegisterForm: HTMLFormElement;
let adminRegisterEmailInput: HTMLInputElement;
let adminRegisterPasswordInput: HTMLInputElement;
let adminConfirmPasswordInput: HTMLInputElement;
let adminAccessCodeInput: HTMLInputElement;
let adminRegisterPasswordToggle: HTMLButtonElement;
let adminConfirmPasswordToggle: HTMLButtonElement;
let adminRegisterButton: HTMLButtonElement;
let adminRegisterFormError: HTMLElement;
let successMessage: HTMLElement;
let successMessageText: HTMLElement;

document.addEventListener('DOMContentLoaded', () => {
  initializeElements();
  setupEventListeners();
  checkExistingAuth();
});

function getRequiredElement<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (!element) {
    throw new Error(`Missing element: ${id}`);
  }
  return element as T;
}

function initializeElements(): void {
  adminRegisterForm = getRequiredElement<HTMLFormElement>('adminRegisterForm');
  adminRegisterEmailInput = getRequiredElement<HTMLInputElement>('adminRegisterEmail');
  adminRegisterPasswordInput = getRequiredElement<HTMLInputElement>('adminRegisterPassword');
  adminConfirmPasswordInput = getRequiredElement<HTMLInputElement>('adminConfirmPassword');
  adminAccessCodeInput = getRequiredElement<HTMLInputElement>('adminAccessCode');
  adminRegisterPasswordToggle = getRequiredElement<HTMLButtonElement>('adminRegisterPasswordToggle');
  adminConfirmPasswordToggle = getRequiredElement<HTMLButtonElement>('adminConfirmPasswordToggle');
  adminRegisterButton = getRequiredElement<HTMLButtonElement>('adminRegisterButton');
  adminRegisterFormError = getRequiredElement<HTMLElement>('adminRegisterFormError');
  successMessage = getRequiredElement<HTMLElement>('successMessage');
  successMessageText = getRequiredElement<HTMLElement>('successMessageText');
}

function setupEventListeners(): void {
  adminRegisterForm.addEventListener('submit', handleAdminRegistration);

  adminRegisterPasswordToggle.addEventListener('click', () => togglePassword('adminRegisterPassword', 'adminRegisterEyeIcon'));
  adminConfirmPasswordToggle.addEventListener('click', () => togglePassword('adminConfirmPassword', 'adminConfirmEyeIcon'));

  adminRegisterEmailInput.addEventListener('blur', () => validateEmail(adminRegisterEmailInput, 'adminRegisterEmailError'));
  adminRegisterPasswordInput.addEventListener('blur', () => validatePassword(adminRegisterPasswordInput));
  adminConfirmPasswordInput.addEventListener('blur', () => validatePasswordMatch());
  adminAccessCodeInput.addEventListener('blur', () => validateRequired(adminAccessCodeInput, 'adminAccessCodeError', 'Admin access code'));
}

function checkExistingAuth(): void {
  if (authService.isAuthenticated() && authService.accessToken) {
    if (!authService.isTokenExpired(authService.accessToken)) {
      const decoded = authService.decodeToken(authService.accessToken) as { is_admin?: boolean } | null;
      if (decoded && decoded.is_admin) {
        window.location.href = '/admin/dashboard.html';
      } else {
        authService.logout();
      }
    } else {
      authService.logout();
    }
  }
}

async function handleAdminRegistration(e: Event): Promise<void> {
  e.preventDefault();

  const email = adminRegisterEmailInput.value.trim();
  const password = adminRegisterPasswordInput.value;
  const confirmPassword = adminConfirmPasswordInput.value;
  const accessCode = adminAccessCodeInput.value.trim();

  let isValid = true;
  isValid = validateEmail(adminRegisterEmailInput, 'adminRegisterEmailError') && isValid;
  isValid = validatePassword(adminRegisterPasswordInput) && isValid;
  isValid = validatePasswordMatch() && isValid;
  isValid = validateRequired(adminAccessCodeInput, 'adminAccessCodeError', 'Admin access code') && isValid;

  if (!isValid) {
    return;
  }

  clearErrors();
  setLoading(adminRegisterButton, true);

  try {
    const response = await fetch(`${authService.baseURL}/auth/register-admin`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: email,
        password: password,
        access_code: accessCode,
      }),
    });

    if (!response.ok) {
      const error = (await response.json()) as { detail?: string };
      throw new Error(error.detail || 'Admin registration failed');
    }

    const data = (await response.json()) as { access_token: string; refresh_token: string };
    authService.storeTokens(data.access_token, data.refresh_token);

    const decoded = authService.decodeToken(data.access_token) as { is_admin?: boolean } | null;
    if (!decoded || !decoded.is_admin) {
      authService.logout();
      throw new Error('Registration failed: Not granted admin privileges');
    }

    showSuccess('Admin registration successful! Redirecting to admin dashboard...');

    setTimeout(() => {
      window.location.href = '/admin/dashboard.html';
    }, 2000);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Admin registration failed. Please check your access code.';
    if (message.includes('fetch') || message.includes('NetworkError')) {
      showError(adminRegisterFormError, 'Admin registration endpoint not available. Please contact system administrator.');
    } else {
      showError(adminRegisterFormError, message);
    }
    setLoading(adminRegisterButton, false);
  }
}

function validateRequired(inputElement: HTMLInputElement, errorId: string, fieldName: string): boolean {
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

function validateEmail(inputElement: HTMLInputElement, errorId: string): boolean {
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

function validatePassword(inputElement: HTMLInputElement): boolean {
  const password = inputElement.value;
  const errorElement = document.getElementById('adminRegisterPasswordError');

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

function validatePasswordMatch(): boolean {
  const password = adminRegisterPasswordInput.value;
  const confirmPassword = adminConfirmPasswordInput.value;
  const errorElement = document.getElementById('adminConfirmPasswordError');

  if (!confirmPassword) {
    showError(errorElement, 'Please confirm your password.');
    adminConfirmPasswordInput.classList.add('error');
    return false;
  }

  if (password !== confirmPassword) {
    showError(errorElement, 'Passwords do not match.');
    adminConfirmPasswordInput.classList.add('error');
    return false;
  }

  adminConfirmPasswordInput.classList.remove('error');
  if (errorElement) {
    errorElement.textContent = '';
  }
  return true;
}

function togglePassword(inputId: string, iconId: string): void {
  const input = getRequiredElement<HTMLInputElement>(inputId);
  const icon = getRequiredElement<HTMLElement>(iconId);
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

function showError(element: HTMLElement | null, message: string): void {
  if (element) {
    element.textContent = message;
    element.classList.add('visible');
  }
}

function clearErrors(): void {
  const errorElements = document.querySelectorAll<HTMLElement>('.form-error, .form-error-message');
  errorElements.forEach((el) => {
    el.textContent = '';
    el.classList.remove('visible');
  });

  const inputs = document.querySelectorAll<HTMLElement>('.form-input');
  inputs.forEach((input) => input.classList.remove('error'));
}

function setLoading(button: HTMLButtonElement, isLoading: boolean): void {
  if (isLoading) {
    button.classList.add('loading');
    button.disabled = true;
  } else {
    button.classList.remove('loading');
    button.disabled = false;
  }
}

function showSuccess(message: string): void {
  successMessageText.textContent = message;
  successMessage.classList.add('visible');

  setTimeout(() => {
    successMessage.classList.remove('visible');
  }, 5000);
}
