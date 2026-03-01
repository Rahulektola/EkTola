import { AuthService } from './auth.js';
/**
 * Jeweller Registration Page Logic
 */
const authService = new AuthService();
let registerForm;
let businessNameInput;
let phoneNumberInput;
let registerEmailInput;
let registerPasswordInput;
let confirmPasswordInput;
let registerPasswordToggle;
let confirmPasswordToggle;
let registerButton;
let registerFormError;
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
    registerForm = getRequiredElement('registerForm');
    businessNameInput = getRequiredElement('businessName');
    phoneNumberInput = getRequiredElement('phoneNumber');
    registerEmailInput = getRequiredElement('registerEmail');
    registerPasswordInput = getRequiredElement('registerPassword');
    confirmPasswordInput = getRequiredElement('confirmPassword');
    registerPasswordToggle = getRequiredElement('registerPasswordToggle');
    confirmPasswordToggle = getRequiredElement('confirmPasswordToggle');
    registerButton = getRequiredElement('registerButton');
    registerFormError = getRequiredElement('registerFormError');
    successMessage = getRequiredElement('successMessage');
    successMessageText = getRequiredElement('successMessageText');
}
function setupEventListeners() {
    registerForm.addEventListener('submit', handleRegistration);
    registerPasswordToggle.addEventListener('click', () => togglePassword('registerPassword', 'registerEyeIcon'));
    confirmPasswordToggle.addEventListener('click', () => togglePassword('confirmPassword', 'confirmEyeIcon'));
    businessNameInput.addEventListener('blur', () => validateRequired(businessNameInput, 'businessNameError', 'Business name'));
    phoneNumberInput.addEventListener('blur', () => validatePhone(phoneNumberInput));
    registerEmailInput.addEventListener('blur', () => validateEmail(registerEmailInput, 'registerEmailError'));
    registerPasswordInput.addEventListener('blur', () => validatePassword(registerPasswordInput));
    confirmPasswordInput.addEventListener('blur', () => validatePasswordMatch());
}
function checkExistingAuth() {
    if (authService.isAuthenticated() && authService.accessToken) {
        if (!authService.isTokenExpired(authService.accessToken)) {
            window.location.href = '/dashboard.html';
        }
        else {
            authService.logout();
        }
    }
}
async function handleRegistration(e) {
    e.preventDefault();
    const businessName = businessNameInput.value.trim();
    const phoneNumber = phoneNumberInput.value.trim();
    const email = registerEmailInput.value.trim();
    const password = registerPasswordInput.value;
    const confirmPassword = confirmPasswordInput.value;
    let isValid = true;
    isValid = validateRequired(businessNameInput, 'businessNameError', 'Business name') && isValid;
    isValid = validatePhone(phoneNumberInput) && isValid;
    isValid = validateEmail(registerEmailInput, 'registerEmailError') && isValid;
    isValid = validatePassword(registerPasswordInput) && isValid;
    isValid = validatePasswordMatch() && isValid;
    if (!isValid) {
        return;
    }
    clearErrors();
    setLoading(registerButton, true);
    try {
        await authService.register({
            business_name: businessName,
            phone_number: phoneNumber,
            email: email,
            password: password,
        });
        showSuccess('Registration successful! Your account is pending admin approval. Redirecting to dashboard...');
        setTimeout(() => {
            window.location.href = '/dashboard.html';
        }, 2500);
    }
    catch (error) {
        const message = error instanceof Error ? error.message : 'Registration failed. Please try again.';
        showError(registerFormError, message);
        setLoading(registerButton, false);
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
//# sourceMappingURL=register.js.map