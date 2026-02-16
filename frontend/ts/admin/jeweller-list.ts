/**
 * Jeweller List Management
 * Filter, search, and paginate jewellers
 */

import { AuthService } from '../auth.js';
import {
    checkAdminAuth,
    AdminNavigation,
    PaginationControls,
    formatDateOnly,
    formatNumber,
    createStatusBadge,
    showToast,
    apiRequest,
    ConfirmationModal
} from './admin-common.js';

const authService = (window as any).authService as AuthService;

interface JewellerListItem {
    id: number;
    business_name: string;
    owner_name: string | null;
    phone_number: string;
    approval_status: string;
    created_at: string;
    total_contacts: number;
    total_campaigns: number;
    is_active: boolean;
}

interface JewellerListResponse {
    jewellers: JewellerListItem[];
    total: number;
    page: number;
    page_size: number;
    pending_count: number;
    approved_count: number;
    rejected_count: number;
}

// State
let currentPage = 1;
let currentPageSize = 20;
let currentStatus = 'all';
let currentSearch = '';
let paginationControls: PaginationControls | null = null;

// DOM Elements
let jewellersTable: HTMLElement;

document.addEventListener('DOMContentLoaded', () => {
    if (!checkAdminAuth(authService)) {
        return;
    }

    new AdminNavigation('admin-nav-container', 'jewellers');

    jewellersTable = document.getElementById('jewellers-table')!;

    setupEventListeners();
    loadJewellers();
});

/**
 * Setup event listeners
 */
function setupEventListeners(): void {
    // Status filter tabs
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            currentStatus = (tab as HTMLElement).dataset.status || 'all';
            currentPage = 1;
            loadJewellers();
        });
    });

    // Search input with debounce
    const searchInput = document.getElementById('search-input') as HTMLInputElement;
    let searchTimeout: number;
    
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = window.setTimeout(() => {
            currentSearch = searchInput.value.trim();
            currentPage = 1;
            loadJewellers();
        }, 500); // Debounce 500ms
    });
}

/**
 * Load jewellers from API
 */
async function loadJewellers(): Promise<void> {
    jewellersTable.innerHTML = '<tr><td colspan="8" class="text-center">Loading...</td></tr>';

    try {
        const params = new URLSearchParams({
            page: currentPage.toString(),
            page_size: currentPageSize.toString(),
        });

        if (currentStatus !== 'all') {
            params.append('status', currentStatus);
        }

        if (currentSearch) {
            params.append('q', currentSearch);
        }

        const data = await apiRequest<JewellerListResponse>(
            `/admin/jewellers?${params.toString()}`,
            authService
        );

        updateBadges(data);
        renderJewellers(data.jewellers);
        updatePagination(data);
    } catch (error) {
        console.error('Failed to load jewellers:', error);
        jewellersTable.innerHTML = `
            <tr>
                <td colspan="8" class="text-center error">
                    Failed to load jewellers: ${error instanceof Error ? error.message : 'Unknown error'}
                </td>
            </tr>
        `;
    }
}

/**
 * Update filter badge counts
 */
function updateBadges(data: JewellerListResponse): void {
    document.getElementById('badge-all')!.textContent = formatNumber(data.total);
    document.getElementById('badge-pending')!.textContent = formatNumber(data.pending_count);
    document.getElementById('badge-approved')!.textContent = formatNumber(data.approved_count);
    document.getElementById('badge-rejected')!.textContent = formatNumber(data.rejected_count);
}

/**
 * Render jewellers table
 */
function renderJewellers(jewellers: JewellerListItem[]): void {
    if (jewellers.length === 0) {
        jewellersTable.innerHTML = '<tr><td colspan="8" class="text-center">No jewellers found</td></tr>';
        return;
    }

    jewellersTable.innerHTML = jewellers.map(jeweller => `
        <tr>
            <td>
                <a href="/admin/jeweller-detail.html?id=${jeweller.id}" class="link-primary">
                    ${jeweller.business_name}
                </a>
            </td>
            <td>${jeweller.owner_name || '-'}</td>
            <td>${jeweller.phone_number}</td>
            <td>${createStatusBadge(jeweller.approval_status)}</td>
            <td>${formatDateOnly(jeweller.created_at)}</td>
            <td>${formatNumber(jeweller.total_contacts)}</td>
            <td>${formatNumber(jeweller.total_campaigns)}</td>
            <td>
                <div class="action-buttons">
                    <button 
                        class="btn btn-sm btn-secondary" 
                        onclick="viewJeweller(${jeweller.id})"
                        title="View Details"
                    >
                        View
                    </button>
                    ${jeweller.approval_status === 'PENDING' ? `
                        <button 
                            class="btn btn-sm btn-success" 
                            onclick="approveJeweller(${jeweller.id})"
                            title="Approve"
                        >
                            Approve
                        </button>
                    ` : ''}
                    <button 
                        class="btn btn-sm btn-admin" 
                        onclick="deleteJeweller(${jeweller.id}, '${jeweller.business_name}')"
                        title="Delete"
                    >
                        Delete
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

/**
 * Update pagination controls
 */
function updatePagination(data: JewellerListResponse): void {
    if (!paginationControls) {
        paginationControls = new PaginationControls(
            'pagination-container',
            data.page,
            data.page_size,
            data.total,
            handlePageChange
        );
    } else {
        paginationControls.update(data.page, data.page_size, data.total);
    }
}

/**
 * Handle page change
 */
function handlePageChange(page: number, pageSize: number): void {
    currentPage = page;
    currentPageSize = pageSize;
    loadJewellers();
}

/**
 * View jeweller details
 */
(window as any).viewJeweller = function(id: number): void {
    window.location.href = `/admin/jeweller-detail.html?id=${id}`;
};

/**
 * Approve jeweller
 */
(window as any).approveJeweller = async function(id: number): Promise<void> {
    const confirmed = await new ConfirmationModal(
        'Approve Jeweller',
        'Are you sure you want to approve this jeweller? They will be able to create campaigns and send messages.',
        'Approve',
        'Cancel'
    ).show();

    if (!confirmed) return;

    try {
        await apiRequest(
            `/admin/jewellers/${id}/approve`,
            authService,
            { method: 'POST' }
        );

        showToast('Jeweller approved successfully', 'success');
        loadJewellers();
    } catch (error) {
        console.error('Failed to approve jeweller:', error);
        showToast(error instanceof Error ? error.message : 'Failed to approve jeweller', 'error');
    }
};

/**
 * Delete jeweller
 */
(window as any).deleteJeweller = async function(id: number, businessName: string): Promise<void> {
    const confirmed = await new ConfirmationModal(
        'Delete Jeweller',
        `Are you sure you want to permanently delete "${businessName}"? This will remove all contacts, campaigns, and messages. This action cannot be undone.`,
        'Delete',
        'Cancel'
    ).show();

    if (!confirmed) return;

    try {
        await apiRequest(
            `/admin/jewellers/${id}`,
            authService,
            { method: 'DELETE' }
        );

        showToast('Jeweller deleted successfully', 'success');
        loadJewellers();
    } catch (error) {
        console.error('Failed to delete jeweller:', error);
        showToast(error instanceof Error ? error.message : 'Failed to delete jeweller', 'error');
    }
};
