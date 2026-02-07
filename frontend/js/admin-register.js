import { AuthService } from './auth.js';
/**
 * Admin Registration Page Logic
 * Note: This requires backend endpoint /auth/register-admin which may not exist yet
 */
const authService = new AuthService();
let adminRegisterForm;
let adminRegisterEmailInput;
let adminRegisterPasswordInput;
let adminConfirmPasswordInput;
let adminAccessCodeInput;
let adminRegisterPasswordToggle;
let adminConfirmPasswordToggle;
let adminRegisterButton;
let adminRegisterFormError;
let successMessage;
let successMessageText;
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
    adminRegisterForm = getRequiredElement('adminRegisterForm');
    adminRegisterEmailInput = getRequiredElement('adminRegisterEmail');
    adminRegisterPasswordInput = getRequiredElement('adminRegisterPassword');
    adminConfirmPasswordInput = getRequiredElement('adminConfirmPassword');
    adminAccessCodeInput = getRequiredElement('adminAccessCode');
    adminRegisterPasswordToggle = getRequiredElement('adminRegisterPasswordToggle');
    adminConfirmPasswordToggle = getRequiredElement('adminConfirmPasswordToggle');
    adminRegisterButton = getRequiredElement('adminRegisterButton');
    adminRegisterFormError = getRequiredElement('adminRegisterFormError');
    successMessage = getRequiredElement('successMessage');
    successMessageText = getRequiredElement('successMessageText');
}
function setupEventListeners() {
    adminRegisterForm.addEventListener('submit', handleAdminRegistration);
    adminRegisterPasswordToggle.addEventListener('click', () => togglePassword('adminRegisterPassword', 'adminRegisterEyeIcon'));
    adminConfirmPasswordToggle.addEventListener('click', () => togglePassword('adminConfirmPassword', 'adminConfirmEyeIcon'));
    adminRegisterEmailInput.addEventListener('blur', () => validateEmail(adminRegisterEmailInput, 'adminRegisterEmailError'));
    adminRegisterPasswordInput.addEventListener('blur', () => validatePassword(adminRegisterPasswordInput));
    adminConfirmPasswordInput.addEventListener('blur', () => validatePasswordMatch());
    adminAccessCodeInput.addEventListener('blur', () => validateRequired(adminAccessCodeInput, 'adminAccessCodeError', 'Admin access code'));
}
function checkExistingAuth() {
    if (authService.isAuthenticated() && authService.accessToken) {
        if (!authService.isTokenExpired(authService.accessToken)) {
            const decoded = authService.decodeToken(authService.accessToken);
            if (decoded && decoded.is_admin) {
                window.location.href = '/admin/dashboard.html';
            }
            else {
                authService.logout();
            }
        }
        else {
            authService.logout();
        }
    }
}
async function handleAdminRegistration(e) {
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
            const error = (await response.json());
            throw new Error(error.detail || 'Admin registration failed');
        }
        const data = (await response.json());
        authService.storeTokens(data.access_token, data.refresh_token);
        const decoded = authService.decodeToken(data.access_token);
        if (!decoded || !decoded.is_admin) {
            authService.logout();
            throw new Error('Registration failed: Not granted admin privileges');
        }
        showSuccess('Admin registration successful! Redirecting to admin dashboard...');
        setTimeout(() => {
            window.location.href = '/admin/dashboard.html';
        }, 2000);
    }
    catch (error) {
        const message = error instanceof Error ? error.message : 'Admin registration failed. Please check your access code.';
        if (message.includes('fetch') || message.includes('NetworkError')) {
            showError(adminRegisterFormError, 'Admin registration endpoint not available. Please contact system administrator.');
        }
        else {
            showError(adminRegisterFormError, message);
        }
        setLoading(adminRegisterButton, false);
    }
}
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
function validatePassword(inputElement) {
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
function validatePasswordMatch() {
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
function togglePassword(inputId, iconId) {
    const input = getRequiredElement(inputId);
    const icon = getRequiredElement(iconId);
    const type = input.type === 'password' ? 'text' : 'password';
    input.type = type;
    if (type === 'text') {
        icon.innerHTML = `
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
      <line x1="1" y1="1" x2="23" y2="23"></line>
    `;
    }
    else {
        icon.innerHTML = `
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
      <circle cx="12" cy="12" r="3"></circle>
    `;
    }
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
    }, 5000);
}
//# sourceMappingURL=admin-register.js.map