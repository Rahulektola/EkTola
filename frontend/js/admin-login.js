import { AuthService } from './auth.js';
/**
 * Admin Login Page Logic
 * Handles admin-only authentication with role verification
 */
const authService = new AuthService();
let adminLoginForm;
let adminEmailInput;
let adminPasswordInput;
let adminPasswordToggle;
let adminLoginButton;
let adminFormError;
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
    adminLoginForm = getRequiredElement('adminLoginForm');
    adminEmailInput = getRequiredElement('adminEmail');
    adminPasswordInput = getRequiredElement('adminPassword');
    adminPasswordToggle = getRequiredElement('adminPasswordToggle');
    adminLoginButton = getRequiredElement('adminLoginButton');
    adminFormError = getRequiredElement('adminFormError');
    successMessage = getRequiredElement('successMessage');
    successMessageText = getRequiredElement('successMessageText');
}
function setupEventListeners() {
    adminLoginForm.addEventListener('submit', handleAdminLogin);
    adminPasswordToggle.addEventListener('click', toggleAdminPassword);
    adminEmailInput.addEventListener('blur', () => validateEmail(adminEmailInput, 'adminEmailError'));
}
function checkExistingAuth() {
    if (authService.isAuthenticated() && authService.accessToken) {
        if (!authService.isTokenExpired(authService.accessToken)) {
            const decoded = authService.decodeToken(authService.accessToken);
            if (decoded && decoded.is_admin) {
                showSuccess('Already logged in. Redirecting to admin dashboard...');
                setTimeout(() => {
                    window.location.href = '/admin/dashboard.html';
                }, 1000);
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
async function handleAdminLogin(e) {
    e.preventDefault();
    const email = adminEmailInput.value.trim();
    const password = adminPasswordInput.value;
    if (!validateEmail(adminEmailInput, 'adminEmailError') || !password) {
        return;
    }
    clearErrors();
    setLoading(adminLoginButton, true);
    try {
        const response = await authService.login(email, password);
        const decoded = authService.decodeToken(response.access_token);
        if (!decoded || !decoded.is_admin) {
            showError(adminFormError, 'This account does not have admin privileges. Please use the jeweller login.');
            authService.logout();
            setLoading(adminLoginButton, false);
            return;
        }
        showSuccess('Admin login successful! Redirecting to admin dashboard...');
        setTimeout(() => {
            window.location.href = '/admin/dashboard.html';
        }, 1500);
    }
    catch (error) {
        const message = error instanceof Error ? error.message : 'Admin login failed. Please check your credentials.';
        showError(adminFormError, message);
        setLoading(adminLoginButton, false);
    }
}
function toggleAdminPassword() {
    const type = adminPasswordInput.type === 'password' ? 'text' : 'password';
    adminPasswordInput.type = type;
    const eyeIcon = getRequiredElement('adminEyeIcon');
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
//# sourceMappingURL=admin-login.js.map