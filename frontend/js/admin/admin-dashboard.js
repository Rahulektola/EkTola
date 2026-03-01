/**
 * Admin Dashboard - Main Page
 * Displays KPI overview and jeweller performance table
 */
import { checkAdminAuth, AdminNavigation, formatNumber, formatPercentage, formatDate, showToast, apiRequest, ConfirmationModal } from './admin-common.js';
const authService = window.authService;
// DOM Elements
let loadingState;
let errorState;
let kpiContainer;
let jewellersTableBody;
document.addEventListener('DOMContentLoaded', () => {
    // Check admin authentication
    if (!checkAdminAuth(authService)) {
        return;
    }
    // Initialize navigation
    new AdminNavigation('admin-nav-container', 'dashboard');
    // Get DOM elements
    loadingState = document.getElementById('loading-state');
    errorState = document.getElementById('error-state');
    kpiContainer = document.getElementById('kpi-container');
    jewellersTableBody = document.getElementById('jewellers-table-body');
    // Display admin email
    const decoded = authService.decodeToken(authService.accessToken);
    const adminEmailEl = document.getElementById('admin-email');
    if (adminEmailEl && (decoded === null || decoded === void 0 ? void 0 : decoded.email)) {
        adminEmailEl.textContent = decoded.email;
    }
    // Load dashboard data
    loadDashboard();
});
/**
 * Load dashboard data from API
 */
async function loadDashboard() {
    showLoading(true);
    hideError();
    try {
        const data = await apiRequest('/analytics/admin/dashboard', authService);
        updateKPIs(data);
        updateJewellersTable(data.jeweller_stats);
        showLoading(false);
    }
    catch (error) {
        console.error('Failed to load dashboard:', error);
        showError(error instanceof Error ? error.message : 'Failed to load dashboard');
        showLoading(false);
    }
}
/**
 * Update KPI cards with data
 */
function updateKPIs(data) {
    document.getElementById('kpi-total-jewellers').textContent = formatNumber(data.total_jewellers);
    document.getElementById('kpi-active-jewellers').textContent = formatNumber(data.active_jewellers);
    document.getElementById('kpi-total-contacts').textContent = formatNumber(data.total_contacts_across_jewellers);
    document.getElementById('kpi-messages-30d').textContent = formatNumber(data.messages_last_30_days);
    document.getElementById('kpi-delivery-rate').textContent = formatPercentage(data.overall_delivery_rate);
    document.getElementById('kpi-read-rate').textContent = formatPercentage(data.overall_read_rate);
}
/**
 * Update jewellers performance table
 */
function updateJewellersTable(jewellers) {
    if (jewellers.length === 0) {
        jewellersTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center">No jewellers found</td>
            </tr>
        `;
        return;
    }
    jewellersTableBody.innerHTML = jewellers.map(jeweller => `
        <tr data-jeweller-id="${jeweller.jeweller_id}">
            <td>
                <a href="/admin/jeweller-detail.html?id=${jeweller.jeweller_id}" class="link-primary">
                    ${jeweller.business_name}
                </a>
            </td>
            <td>${formatNumber(jeweller.total_contacts)}</td>
            <td>${formatNumber(jeweller.total_campaigns)}</td>
            <td>${formatNumber(jeweller.messages_last_30_days)}</td>
            <td>${formatPercentage(jeweller.delivery_rate)}</td>
            <td>${formatPercentage(jeweller.read_rate)}</td>
            <td>${formatDate(jeweller.last_active)}</td>
            <td>
                <div class="action-buttons">
                    <button 
                        class="btn btn-sm btn-secondary" 
                        onclick="viewJeweller(${jeweller.jeweller_id})"
                        title="View Details"
                    >
                        View
                    </button>
                    <button 
                        class="btn btn-sm btn-admin" 
                        onclick="impersonateJeweller(${jeweller.jeweller_id}, '${jeweller.business_name}')"
                        title="Login as ${jeweller.business_name}"
                    >
                        Login As
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}
/**
 * View jeweller details
 */
window.viewJeweller = function (jewellerId) {
    window.location.href = `/admin/jeweller-detail.html?id=${jewellerId}`;
};
/**
 * Impersonate jeweller
 */
window.impersonateJeweller = async function (jewellerId, businessName) {
    const confirmed = await new ConfirmationModal('Impersonate Jeweller', `You are about to view the dashboard as "${businessName}". You will be able to see their contacts, campaigns, and messages. Exit impersonation mode to return to admin view.`, 'Continue', 'Cancel').show();
    if (!confirmed)
        return;
    try {
        const result = await authService.impersonateJeweller(jewellerId);
        showToast(`Now viewing as ${result.jeweller_name}`, 'success');
        // Redirect to jeweller dashboard after a brief delay
        setTimeout(() => {
            window.location.href = '/dashboard.html';
        }, 1000);
    }
    catch (error) {
        console.error('Impersonation failed:', error);
        showToast(error instanceof Error ? error.message : 'Impersonation failed', 'error');
    }
};
/**
 * Show/hide loading state
 */
function showLoading(show) {
    loadingState.style.display = show ? 'flex' : 'none';
    const dashboardContent = document.getElementById('dashboard-content');
    if (dashboardContent) {
        dashboardContent.style.display = show ? 'none' : 'block';
    }
}
/**
 * Show error message
 */
function showError(message) {
    errorState.style.display = 'block';
    const errorMsg = errorState.querySelector('.error-message');
    if (errorMsg) {
        errorMsg.textContent = message;
    }
    const dashboardContent = document.getElementById('dashboard-content');
    if (dashboardContent) {
        dashboardContent.style.display = 'none';
    }
}
/**
 * Hide error message
 */
function hideError() {
    errorState.style.display = 'none';
}
//# sourceMappingURL=admin-dashboard.js.map