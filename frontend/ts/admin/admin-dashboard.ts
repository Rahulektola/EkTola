/**
 * Admin Dashboard - Main Page
 * Displays KPI overview and jeweller performance table
 */

import { AuthService } from '../auth.js';
import {
    checkAdminAuth,
    AdminNavigation,
    formatNumber,
    formatPercentage,
    formatDate,
    createStatusBadge,
    showToast,
    apiRequest,
    ConfirmationModal
} from './admin-common.js';

const authService = (window as any).authService as AuthService;

interface JewellerStats {
    jeweller_id: number;
    business_name: string;
    total_contacts: number;
    total_campaigns: number;
    total_messages_sent: number;
    messages_last_30_days: number;
    delivery_rate: number;
    read_rate: number;
    last_active: string | null;
}

interface DashboardData {
    total_jewellers: number;
    active_jewellers: number;
    total_contacts_across_jewellers: number;
    total_messages_sent: number;
    messages_last_30_days: number;
    overall_delivery_rate: number;
    overall_read_rate: number;
    jeweller_stats: JewellerStats[];
}

// DOM Elements
let loadingState: HTMLElement;
let errorState: HTMLElement;
let kpiContainer: HTMLElement;
let jewellersTableBody: HTMLElement;

document.addEventListener('DOMContentLoaded', () => {
    // Check admin authentication
    if (!checkAdminAuth(authService)) {
        return;
    }

    // Initialize navigation
    new AdminNavigation('admin-nav-container', 'dashboard');

    // Get DOM elements
    loadingState = document.getElementById('loading-state')!;
    errorState = document.getElementById('error-state')!;
    kpiContainer = document.getElementById('kpi-container')!;
    jewellersTableBody = document.getElementById('jewellers-table-body')!;

    // Display admin email
    const decoded = authService.decodeToken(authService.accessToken!);
    const adminEmailEl = document.getElementById('admin-email');
    if (adminEmailEl && decoded?.email) {
        adminEmailEl.textContent = decoded.email as string;
    }

    // Load dashboard data
    loadDashboard();
});

/**
 * Load dashboard data from API
 */
async function loadDashboard(): Promise<void> {
    showLoading(true);
    hideError();

    try {
        const data = await apiRequest<DashboardData>(
            '/analytics/admin/dashboard',
            authService
        );

        updateKPIs(data);
        updateJewellersTable(data.jeweller_stats);
        
        showLoading(false);
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        showError(error instanceof Error ? error.message : 'Failed to load dashboard');
        showLoading(false);
    }
}

/**
 * Update KPI cards with data
 */
function updateKPIs(data: DashboardData): void {
    document.getElementById('kpi-total-jewellers')!.textContent = formatNumber(data.total_jewellers);
    document.getElementById('kpi-active-jewellers')!.textContent = formatNumber(data.active_jewellers);
    document.getElementById('kpi-total-contacts')!.textContent = formatNumber(data.total_contacts_across_jewellers);
    document.getElementById('kpi-messages-30d')!.textContent = formatNumber(data.messages_last_30_days);
    document.getElementById('kpi-delivery-rate')!.textContent = formatPercentage(data.overall_delivery_rate);
    document.getElementById('kpi-read-rate')!.textContent = formatPercentage(data.overall_read_rate);
}

/**
 * Update jewellers performance table
 */
function updateJewellersTable(jewellers: JewellerStats[]): void {
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
(window as any).viewJeweller = function(jewellerId: number): void {
    window.location.href = `/admin/jeweller-detail.html?id=${jewellerId}`;
};

/**
 * Impersonate jeweller
 */
(window as any).impersonateJeweller = async function(jewellerId: number, businessName: string): Promise<void> {
    const confirmed = await new ConfirmationModal(
        'Impersonate Jeweller',
        `You are about to view the dashboard as "${businessName}". You will be able to see their contacts, campaigns, and messages. Exit impersonation mode to return to admin view.`,
        'Continue',
        'Cancel'
    ).show();

    if (!confirmed) return;

    try {
        const result = await authService.impersonateJeweller(jewellerId);
        showToast(`Now viewing as ${result.jeweller_name}`, 'success');
        
        // Redirect to jeweller dashboard after a brief delay
        setTimeout(() => {
            window.location.href = '/dashboard.html';
        }, 1000);
    } catch (error) {
        console.error('Impersonation failed:', error);
        showToast(error instanceof Error ? error.message : 'Impersonation failed', 'error');
    }
};

/**
 * Show/hide loading state
 */
function showLoading(show: boolean): void {
    loadingState.style.display = show ? 'flex' : 'none';
    const dashboardContent = document.getElementById('dashboard-content');
    if (dashboardContent) {
        dashboardContent.style.display = show ? 'none' : 'block';
    }
}

/**
 * Show error message
 */
function showError(message: string): void {
    errorState.style.display = 'block';
    const errorMsg = errorState.querySelector('.error-message') as HTMLElement;
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
function hideError(): void {
    errorState.style.display = 'none';
}
