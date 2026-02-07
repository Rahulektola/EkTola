import { AuthService } from './auth.js';
/**
 * Login Page Logic
 * Handles form interactions and authentication flows
 */
const authService = new AuthService();
let passwordLoginForm;
let otpRequestForm;
let otpVerifyForm;
let phoneNumberInput;
let passwordInput;
let passwordToggle;
let loginButton;
let loginLoader;
let otpPhoneInput;
let otpCode;
let requestOtpButton;
let verifyOtpButton;
let resendOtpButton;
let formError;
let successMessage;
let successMessageText;
let tabButtons;
let tabContents;
let currentOtpPhone = '';
document.addEventListener('DOMContentLoaded', () => {
    initializeElements();
    setupEventListeners();
    checkExistingAuth();
});
function getRequiredElement(id) {
    const element = document.getElementById(id);
    if (!element) {
        throw new Error(`Missing element: ${id}`);
    }
    return element;
}
function initializeElements() {
    passwordLoginForm = getRequiredElement('passwordLoginForm');
    otpRequestForm = getRequiredElement('otpRequestForm');
    otpVerifyForm = getRequiredElement('otpVerifyForm');
    phoneNumberInput = getRequiredElement('phoneNumber');
    passwordInput = getRequiredElement('password');
    passwordToggle = getRequiredElement('passwordToggle');
    loginButton = getRequiredElement('loginButton');
    loginLoader = getRequiredElement('loginLoader');
    otpPhoneInput = getRequiredElement('otpPhone');
    otpCode = getRequiredElement('otpCode');
    requestOtpButton = getRequiredElement('requestOtpButton');
    verifyOtpButton = getRequiredElement('verifyOtpButton');
    resendOtpButton = getRequiredElement('resendOtpButton');
    formError = getRequiredElement('formError');
    successMessage = getRequiredElement('successMessage');
    successMessageText = getRequiredElement('successMessageText');
    tabButtons = document.querySelectorAll('.tab-button');
    tabContents = document.querySelectorAll('.tab-content');
}
function setupEventListeners() {
    tabButtons.forEach((button) => {
        button.addEventListener('click', () => { var _a; return handleTabChange((_a = button.dataset.tab) !== null && _a !== void 0 ? _a : ''); });
    });
    passwordLoginForm.addEventListener('submit', handlePasswordLogin);
    passwordToggle.addEventListener('click', togglePasswordVisibility);
    otpRequestForm.addEventListener('submit', handleOtpRequest);
    otpVerifyForm.addEventListener('submit', handleOtpVerify);
    resendOtpButton.addEventListener('click', handleResendOtp);
    getRequiredElement('changePhoneButton').addEventListener('click', () => {
        otpRequestForm.classList.add('active');
        otpVerifyForm.classList.remove('active');
        otpCode.value = '';
    });
    getRequiredElement('forgotPasswordLink').addEventListener('click', (e) => {
        e.preventDefault();
        handleTabChange('otp');
        if (phoneNumberInput.value) {
            otpPhoneInput.value = phoneNumberInput.value;
        }
    });
    phoneNumberInput.addEventListener('blur', () => validatePhone(phoneNumberInput));
    otpPhoneInput.addEventListener('blur', () => validatePhone(otpPhoneInput));
    otpCode.addEventListener('input', (e) => {
        const target = e.target;
        if (!target)
            return;
        target.value = target.value.replace(/\D/g, '').slice(0, 6);
    });
}
function checkExistingAuth() {
    if (authService.isAuthenticated() && authService.accessToken) {
        if (!authService.isTokenExpired(authService.accessToken)) {
            showSuccess('Already logged in. Redirecting...');
            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 1000);
        }
        else {
            authService.logout();
        }
    }
}
function handleTabChange(tabName) {
    tabButtons.forEach((button) => {
        if (button.dataset.tab === tabName) {
            button.classList.add('active');
        }
        else {
            button.classList.remove('active');
        }
    });
    tabContents.forEach((content) => {
        if (content.dataset.content === tabName) {
            content.classList.add('active');
        }
        else {
            content.classList.remove('active');
        }
    });
    clearErrors();
}
async function handlePasswordLogin(e) {
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
        const decoded = authService.decodeToken(response.access_token);
        if (decoded && decoded.is_admin) {
            showSuccess('Login successful! Redirecting to admin dashboard...');
            setTimeout(() => {
                window.location.href = '/admin/dashboard.html';
            }, 1500);
        }
        else {
            showSuccess('Login successful! Redirecting to dashboard...');
            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 1500);
        }
    }
    catch (error) {
        const message = error instanceof Error ? error.message : 'Login failed. Please check your credentials.';
        showError(formError, message);
        setLoading(loginButton, false);
    }
}
async function handleOtpRequest(e) {
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
        getRequiredElement('otpPhoneDisplay').textContent = phoneNumber;
        otpRequestForm.classList.remove('active');
        otpVerifyForm.classList.add('active');
        setTimeout(() => otpCode.focus(), 100);
        if (response.otp) {
            console.log('Development OTP:', response.otp);
        }
    }
    catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to send OTP.';
        showError(getRequiredElement('otpRequestError'), message);
        setLoading(requestOtpButton, false);
    }
    finally {
        setLoading(requestOtpButton, false);
    }
}
async function handleOtpVerify(e) {
    e.preventDefault();
    const otp = otpCode.value.trim();
    if (otp.length !== 6) {
        showError(getRequiredElement('otpCodeError'), 'Please enter a 6-digit OTP code.');
        return;
    }
    clearErrors();
    setLoading(verifyOtpButton, true);
    try {
        const response = await authService.verifyPhoneOTP(currentOtpPhone, otp);
        const decoded = authService.decodeToken(response.access_token);
        if (decoded && decoded.is_admin) {
            showSuccess('Login successful! Redirecting to admin dashboard...');
            setTimeout(() => {
                window.location.href = '/admin/dashboard.html';
            }, 1500);
        }
        else {
            showSuccess('Login successful! Redirecting to dashboard...');
            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 1500);
        }
    }
    catch (error) {
        const message = error instanceof Error ? error.message : 'Invalid OTP. Please try again.';
        showError(getRequiredElement('otpVerifyError'), message);
        setLoading(verifyOtpButton, false);
    }
}
async function handleResendOtp() {
    clearErrors();
    setLoading(resendOtpButton, true);
    try {
        await authService.requestPhoneOTP(currentOtpPhone);
        const otpInfo = document.querySelector('.otp-info p');
        if (otpInfo) {
            const originalText = otpInfo.innerHTML;
            otpInfo.innerHTML = '<strong style="color: var(--success-color);">OTP resent successfully!</strong>';
            setTimeout(() => {
                otpInfo.innerHTML = originalText;
            }, 3000);
        }
    }
    catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to resend OTP.';
        showError(getRequiredElement('otpVerifyError'), message);
    }
    finally {
        setLoading(resendOtpButton, false);
    }
}
function togglePasswordVisibility() {
    const type = passwordInput.type === 'password' ? 'text' : 'password';
    passwordInput.type = type;
    const eyeIcon = getRequiredElement('eyeIcon');
    if (type === 'text') {
        eyeIcon.innerHTML = `
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
      <line x1="1" y1="1" x2="23" y2="23"></line>
    `;
    }
    else {
        eyeIcon.innerHTML = `
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
      <circle cx="12" cy="12" r="3"></circle>
    `;
    }
}
function normalizePhoneNumber(phone) {
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
function validatePhone(inputElement) {
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
function showError(element, message) {
    if (element) {
        element.textContent = message;
        element.classList.add('visible');
    }
}
function clearErrors() {
    const errorElements = document.querySelectorAll('.form-error, .form-error-message');
    errorElements.forEach((el) => {
        el.textContent = '';
        el.classList.remove('visible');
    });
    const inputs = document.querySelectorAll('.form-input');
    inputs.forEach((input) => input.classList.remove('error'));
}
function setLoading(button, isLoading) {
    if (isLoading) {
        button.classList.add('loading');
        button.disabled = true;
    }
    else {
        button.classList.remove('loading');
        button.disabled = false;
    }
}
function showSuccess(message) {
    successMessageText.textContent = message;
    successMessage.classList.add('visible');
    setTimeout(() => {
        successMessage.classList.remove('visible');
    }, 3000);
}
document.addEventListener('keypress', (e) => {
    const target = e.target;
    if (e.key === 'Enter' && (target === null || target === void 0 ? void 0 : target.tagName) !== 'TEXTAREA') {
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
//# sourceMappingURL=login.js.map