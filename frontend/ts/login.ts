import { AuthService } from './auth.js';

/**
 * Login Page Logic
 * Handles form interactions and authentication flows
 */

const authService = new AuthService();

let passwordLoginForm: HTMLFormElement;
let otpRequestForm: HTMLFormElement;
let otpVerifyForm: HTMLFormElement;
let phoneNumberInput: HTMLInputElement;
let passwordInput: HTMLInputElement;
let passwordToggle: HTMLButtonElement;
let loginButton: HTMLButtonElement;
let loginLoader: HTMLElement;
let otpPhoneInput: HTMLInputElement;
let otpCode: HTMLInputElement;
let requestOtpButton: HTMLButtonElement;
let verifyOtpButton: HTMLButtonElement;
let resendOtpButton: HTMLButtonElement;
let formError: HTMLElement;
let successMessage: HTMLElement;
let successMessageText: HTMLElement;
let tabButtons: NodeListOf<HTMLButtonElement>;
let tabContents: NodeListOf<HTMLElement>;

let currentOtpPhone = '';

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
  passwordLoginForm = getRequiredElement<HTMLFormElement>('passwordLoginForm');
  otpRequestForm = getRequiredElement<HTMLFormElement>('otpRequestForm');
  otpVerifyForm = getRequiredElement<HTMLFormElement>('otpVerifyForm');

  phoneNumberInput = getRequiredElement<HTMLInputElement>('phoneNumber');
  passwordInput = getRequiredElement<HTMLInputElement>('password');
  passwordToggle = getRequiredElement<HTMLButtonElement>('passwordToggle');
  loginButton = getRequiredElement<HTMLButtonElement>('loginButton');
  loginLoader = getRequiredElement<HTMLElement>('loginLoader');

  otpPhoneInput = getRequiredElement<HTMLInputElement>('otpPhone');
  otpCode = getRequiredElement<HTMLInputElement>('otpCode');
  requestOtpButton = getRequiredElement<HTMLButtonElement>('requestOtpButton');
  verifyOtpButton = getRequiredElement<HTMLButtonElement>('verifyOtpButton');
  resendOtpButton = getRequiredElement<HTMLButtonElement>('resendOtpButton');

  formError = getRequiredElement<HTMLElement>('formError');
  successMessage = getRequiredElement<HTMLElement>('successMessage');
  successMessageText = getRequiredElement<HTMLElement>('successMessageText');

  tabButtons = document.querySelectorAll<HTMLButtonElement>('.tab-button');
  tabContents = document.querySelectorAll<HTMLElement>('.tab-content');
}

function setupEventListeners(): void {
  tabButtons.forEach((button) => {
    button.addEventListener('click', () => handleTabChange(button.dataset.tab ?? ''));
  });

  passwordLoginForm.addEventListener('submit', handlePasswordLogin);
  passwordToggle.addEventListener('click', togglePasswordVisibility);
  otpRequestForm.addEventListener('submit', handleOtpRequest);
  otpVerifyForm.addEventListener('submit', handleOtpVerify);
  resendOtpButton.addEventListener('click', handleResendOtp);

  getRequiredElement<HTMLButtonElement>('changePhoneButton').addEventListener('click', () => {
    otpRequestForm.classList.add('active');
    otpVerifyForm.classList.remove('active');
    otpCode.value = '';
  });

  getRequiredElement<HTMLAnchorElement>('forgotPasswordLink').addEventListener('click', (e) => {
    e.preventDefault();
    handleTabChange('otp');
    if (phoneNumberInput.value) {
      otpPhoneInput.value = phoneNumberInput.value;
    }
  });

  phoneNumberInput.addEventListener('blur', () => validatePhone(phoneNumberInput));
  otpPhoneInput.addEventListener('blur', () => validatePhone(otpPhoneInput));

  otpCode.addEventListener('input', (e) => {
    const target = e.target as HTMLInputElement | null;
    if (!target) return;
    target.value = target.value.replace(/\D/g, '').slice(0, 6);
  });
}

function checkExistingAuth(): void {
  if (authService.isAuthenticated() && authService.accessToken) {
    if (!authService.isTokenExpired(authService.accessToken)) {
      showSuccess('Already logged in. Redirecting...');
      setTimeout(() => {
        window.location.href = '/dashboard.html';
      }, 1000);
    } else {
      authService.logout();
    }
  }
}

function handleTabChange(tabName: string): void {
  tabButtons.forEach((button) => {
    if (button.dataset.tab === tabName) {
      button.classList.add('active');
    } else {
      button.classList.remove('active');
    }
  });

  tabContents.forEach((content) => {
    if (content.dataset.content === tabName) {
      content.classList.add('active');
    } else {
      content.classList.remove('active');
    }
  });

  clearErrors();
}

async function handlePasswordLogin(e: Event): Promise<void> {
  e.preventDefault();

  const phoneNumber = phoneNumberInput.value.trim();
  const password = passwordInput.value;

  if (!validatePhone(phoneNumberInput) || !password) {
    return;
  }

  clearErrors();
  setLoading(loginButton, true);

  try {
    const response = await authService.loginWithPhone(phoneNumber, password);
    const decoded = authService.decodeToken(response.access_token) as { is_admin?: boolean } | null;

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
    const message = error instanceof Error ? error.message : 'Login failed. Please check your credentials.';
    showError(formError, message);
    setLoading(loginButton, false);
  }
}

async function handleOtpRequest(e: Event): Promise<void> {
  e.preventDefault();

  const phoneNumber = otpPhoneInput.value.trim();

  if (!validatePhone(otpPhoneInput)) {
    return;
  }

  clearErrors();
  setLoading(requestOtpButton, true);

  try {
    const response = await authService.requestPhoneOTP(phoneNumber);

    currentOtpPhone = phoneNumber;
    getRequiredElement<HTMLElement>('otpPhoneDisplay').textContent = phoneNumber;

    otpRequestForm.classList.remove('active');
    otpVerifyForm.classList.add('active');

    setTimeout(() => otpCode.focus(), 100);

    if (response.otp) {
      console.log('Development OTP:', response.otp);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to send OTP.';
    showError(getRequiredElement<HTMLElement>('otpRequestError'), message);
    setLoading(requestOtpButton, false);
  } finally {
    setLoading(requestOtpButton, false);
  }
}

async function handleOtpVerify(e: Event): Promise<void> {
  e.preventDefault();

  const otp = otpCode.value.trim();

  if (otp.length !== 6) {
    showError(getRequiredElement<HTMLElement>('otpCodeError'), 'Please enter a 6-digit OTP code.');
    return;
  }

  clearErrors();
  setLoading(verifyOtpButton, true);

  try {
    const response = await authService.verifyPhoneOTP(currentOtpPhone, otp);
    const decoded = authService.decodeToken(response.access_token) as { is_admin?: boolean } | null;

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
    const message = error instanceof Error ? error.message : 'Invalid OTP. Please try again.';
    showError(getRequiredElement<HTMLElement>('otpVerifyError'), message);
    setLoading(verifyOtpButton, false);
  }
}

async function handleResendOtp(): Promise<void> {
  clearErrors();
  setLoading(resendOtpButton, true);

  try {
    await authService.requestPhoneOTP(currentOtpPhone);

    const otpInfo = document.querySelector<HTMLElement>('.otp-info p');
    if (otpInfo) {
      const originalText = otpInfo.innerHTML;
      otpInfo.innerHTML = '<strong style="color: var(--success-color);">OTP resent successfully!</strong>';
      setTimeout(() => {
        otpInfo.innerHTML = originalText;
      }, 3000);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to resend OTP.';
    showError(getRequiredElement<HTMLElement>('otpVerifyError'), message);
  } finally {
    setLoading(resendOtpButton, false);
  }
}

function togglePasswordVisibility(): void {
  const type = passwordInput.type === 'password' ? 'text' : 'password';
  passwordInput.type = type;

  const eyeIcon = getRequiredElement<HTMLElement>('eyeIcon');
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

function normalizePhoneNumber(phone: string): string {
  let cleaned = phone.replace(/[\s\-\(\)]/g, '');

  if (cleaned.startsWith('+91')) {
    return cleaned;
  }

  if (cleaned.startsWith('91') && cleaned.length === 12) {
    return '+' + cleaned;
  }

  if (/^[6-9]\d{9}$/.test(cleaned)) {
    return '+91' + cleaned;
  }

  return cleaned;
}

function validatePhone(inputElement: HTMLInputElement): boolean {
  const phone = inputElement.value.trim();
  const errorElement = document.getElementById(inputElement.id + 'Error');

  if (!phone) {
    showError(errorElement, 'Phone number is required.');
    inputElement.classList.add('error');
    return false;
  }

  const normalized = normalizePhoneNumber(phone);
  const phoneRegex = /^\+[1-9]\d{1,14}$/;

  if (!phoneRegex.test(normalized)) {
    showError(errorElement, 'Please enter a valid 10-digit mobile number.');
    inputElement.classList.add('error');
    return false;
  }

  inputElement.value = normalized;

  inputElement.classList.remove('error');
  if (errorElement) {
    errorElement.textContent = '';
  }
  return true;
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
  }, 3000);
}

document.addEventListener('keypress', (e: KeyboardEvent) => {
  const target = e.target as HTMLElement | null;
  if (e.key === 'Enter' && target?.tagName !== 'TEXTAREA') {
    const activeForm = document.querySelector<HTMLElement>('.auth-form.active form, .otp-step.active');
    if (activeForm) {
      const submitButton = activeForm.querySelector<HTMLButtonElement>('button[type="submit"]');
      if (submitButton && !submitButton.disabled) {
        e.preventDefault();
        submitButton.click();
      }
    }
  }
});
