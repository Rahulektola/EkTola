/**
 * Deleted Contacts Management Page
 * View, restore, and purge soft-deleted contacts
 */

import '@/services/auth';  // Initialize global authService
import {
    checkAdminAuth,
    AdminNavigation,
    formatDate,
    showToast,
    apiRequest,
    clearError,
    showError,
    setButtonLoading
} from '@/admin/common';
import type { AuthService } from '@/services/auth';

const authService = window.authService as AuthService;

interface DeletedContact {
    id: number;
    jeweller_id: number;
    phone_number: string;
    name: string | null;
    customer_id: string | null;
    segment: string;
    preferred_language: string;
    deleted_at: string | null;
    days_since_deletion: number;
}

interface DeletedContactsResponse {
    contacts: DeletedContact[];
    total: number;
    page: number;
    page_size: number;
    jeweller_id: number | null;
    jeweller_name: string | null;
}

interface JewellerOption {
    id: number;
    business_name: string;
}

interface PurgeRequest {
    older_than_days: number;
    jeweller_id: number | null;
}

interface PurgeResponse {
    purged_count: number;
    message: string;
    jeweller_id: number | null;
    older_than_days: number;
}

interface RestoreRequest {
    contact_ids: number[];
}

interface RestoreResponse {
    restored_count: number;
    failed_count: number;
    message: string;
    restored_ids: number[];
    failed_ids: number[];
}

// State
let currentPage = 1;
const pageSize = 50;
let selectedContactIds = new Set<number>();
let allJewellers: JewellerOption[] = [];
let currentFilters = {
    jewellerId: null as number | null,
    olderThanDays: null as number | null
};

// DOM Elements
let loadingState: HTMLElement;
let errorState: HTMLElement;
let contentContainer: HTMLElement;

document.addEventListener('DOMContentLoaded', () => {
    if (!checkAdminAuth(authService)) {
        return;
    }

    new AdminNavigation('admin-nav-container', 'deleted-contacts');

    loadingState = document.getElementById('loading-state')!;
    errorState = document.getElementById('error-state')!;
    contentContainer = document.getElementById('content-container')!;

    setupEventListeners();
    loadJewellers();
    loadDeletedContacts();
});

/**
 * Setup event listeners
 */
function setupEventListeners(): void {
    // Filter and actions
    document.getElementById('btn-apply-filters')?.addEventListener('click', applyFilters);
    document.getElementById('btn-restore-selected')?.addEventListener('click', restoreSelected);
    document.getElementById('btn-purge-old')?.addEventListener('click', openPurgeModal);
    
    // Select all checkbox
    document.getElementById('select-all')?.addEventListener('change', (e) => {
        const checked = (e.target as HTMLInputElement).checked;
        document.querySelectorAll('.contact-checkbox').forEach(checkbox => {
            (checkbox as HTMLInputElement).checked = checked;
            const id = parseInt((checkbox as HTMLInputElement).dataset.contactId!);
            if (checked) {
                selectedContactIds.add(id);
            } else {
                selectedContactIds.delete(id);
            }
        });
        updateSelectedCount();
    });

    // Purge modal
    document.getElementById('btn-confirm-purge')?.addEventListener('click', confirmPurge);
}

/**
 * Load list of jewellers for filters
 */
async function loadJewellers(): Promise<void> {
    try {
        const response = await apiRequest<{ jewellers: JewellerOption[] }>(
            '/admin/jewellers?page_size=1000',
            authService
        );
        allJewellers = response.jewellers;

        // Populate filter dropdowns
        const filterSelect = document.getElementById('filter-jeweller') as HTMLSelectElement;
        const purgeSelect = document.getElementById('purge-jeweller') as HTMLSelectElement;

        allJewellers.forEach(jeweller => {
            const option1 = new Option(jeweller.business_name, jeweller.id.toString());
            const option2 = new Option(jeweller.business_name, jeweller.id.toString());
            filterSelect.add(option1);
            purgeSelect.add(option2);
        });
    } catch (error) {
        console.error('Failed to load jewellers:', error);
    }
}

/**
 * Apply filters and reload
 */
function applyFilters(): void {
    const jewellerSelect = document.getElementById('filter-jeweller') as HTMLSelectElement;
    const daysSelect = document.getElementById('filter-days') as HTMLSelectElement;

    currentFilters.jewellerId = jewellerSelect.value ? parseInt(jewellerSelect.value) : null;
    currentFilters.olderThanDays = daysSelect.value ? parseInt(daysSelect.value) : null;
    
    currentPage = 1;
    selectedContactIds.clear();
    loadDeletedContacts();
}

/**
 * Load deleted contacts from API
 */
async function loadDeletedContacts(): Promise<void> {
    loadingState.style.display = 'flex';
    errorState.style.display = 'none';
    contentContainer.style.display = 'none';

    try {
        const params = new URLSearchParams({
            page: currentPage.toString(),
            page_size: pageSize.toString()
        });

        if (currentFilters.jewellerId) {
            params.append('jeweller_id', currentFilters.jewellerId.toString());
        }
        if (currentFilters.olderThanDays) {
            params.append('older_than_days', currentFilters.olderThanDays.toString());
        }

        const data = await apiRequest<DeletedContactsResponse>(
            `/admin/contacts/deleted?${params}`,
            authService
        );

        displayDeletedContacts(data);
        
        loadingState.style.display = 'none';
        contentContainer.style.display = 'block';
    } catch (error) {
        console.error('Failed to load deleted contacts:', error);
        loadingState.style.display = 'none';
        errorState.style.display = 'block';
        const errorMsg = errorState.querySelector('.error-message') as HTMLElement;
        errorMsg.textContent = error instanceof Error ? error.message : 'Failed to load deleted contacts';
    }
}

/**
 * Display deleted contacts in table
 */
function displayDeletedContacts(data: DeletedContactsResponse): void {
    // Update stats
    document.getElementById('stat-total')!.textContent = data.total.toString();
    updateSelectedCount();

    const tableContainer = document.getElementById('contacts-table')!;

    if (data.contacts.length === 0) {
        tableContainer.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">No deleted contacts found.</p>';
        document.getElementById('pagination')!.innerHTML = '';
        return;
    }

    // Build table
    const table = `
        <table class="data-table">
            <thead>
                <tr>
                    <th width="40">Select</th>
                    <th>Name</th>
                    <th>Phone Number</th>
                    <th>Customer ID</th>
                    <th>Segment</th>
                    <th>Jeweller ID</th>
                    <th>Deleted At</th>
                    <th>Days Ago</th>
                </tr>
            </thead>
            <tbody>
                ${data.contacts.map(contact => `
                    <tr>
                        <td>
                            <input 
                                type="checkbox" 
                                class="contact-checkbox" 
                                data-contact-id="${contact.id}"
                                ${selectedContactIds.has(contact.id) ? 'checked' : ''}
                            >
                        </td>
                        <td>${contact.name || '-'}</td>
                        <td>${contact.phone_number}</td>
                        <td>${contact.customer_id || '-'}</td>
                        <td><span class="badge badge-${contact.segment.toLowerCase()}">${contact.segment}</span></td>
                        <td>${contact.jeweller_id}</td>
                        <td>${contact.deleted_at ? formatDate(contact.deleted_at) : '-'}</td>
                        <td>${contact.days_since_deletion} days</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    tableContainer.innerHTML = table;

    // Add checkbox listeners
    document.querySelectorAll('.contact-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const id = parseInt((e.target as HTMLInputElement).dataset.contactId!);
            if ((e.target as HTMLInputElement).checked) {
                selectedContactIds.add(id);
            } else {
                selectedContactIds.delete(id);
            }
            updateSelectedCount();
        });
    });

    // Build pagination
    renderPagination(data.total, data.page, data.page_size);
}

/**
 * Render pagination controls
 */
function renderPagination(total: number, page: number, pageSize: number): void {
    const totalPages = Math.ceil(total / pageSize);
    const paginationContainer = document.getElementById('pagination')!;

    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }

    let html = '<div class="pagination-controls">';

    // Previous button
    if (page > 1) {
        html += `<button class="btn btn-secondary btn-sm" onclick="window.goToPage(${page - 1})">Previous</button>`;
    }

    // Page numbers
    html += `<span style="margin: 0 1rem;">Page ${page} of ${totalPages}</span>`;

    // Next button
    if (page < totalPages) {
        html += `<button class="btn btn-secondary btn-sm" onclick="window.goToPage(${page + 1})">Next</button>`;
    }

    html += '</div>';
    paginationContainer.innerHTML = html;
}

/**
 * Go to specific page
 */
(window as any).goToPage = function(page: number): void {
    currentPage = page;
    loadDeletedContacts();
};

/**
 * Update selected count and enable/disable restore button
 */
function updateSelectedCount(): void {
    const count = selectedContactIds.size;
    document.getElementById('stat-selected')!.textContent = count.toString();
    
    const restoreBtn = document.getElementById('btn-restore-selected') as HTMLButtonElement;
    restoreBtn.disabled = count === 0;
}

/**
 * Restore selected contacts
 */
async function restoreSelected(): Promise<void> {
    if (selectedContactIds.size === 0) {
        return;
    }

    const confirmed = confirm(`Are you sure you want to restore ${selectedContactIds.size} contacts?`);
    if (!confirmed) {
        return;
    }

    const restoreBtn = document.getElementById('btn-restore-selected')! as HTMLButtonElement;
    setButtonLoading(restoreBtn, true);

    try {
        const result = await apiRequest<RestoreResponse>(
            '/admin/contacts/restore',
            authService,
            {
                method: 'POST',
                body: JSON.stringify({
                    contact_ids: Array.from(selectedContactIds)
                })
            }
        );

        setButtonLoading(restoreBtn, false);
        showToast(`Restored ${result.restored_count} contacts`, 'success');
        
        if (result.failed_count > 0) {
            showToast(`${result.failed_count} contacts failed to restore`, 'error');
        }

        selectedContactIds.clear();
        loadDeletedContacts();
    } catch (error) {
        setButtonLoading(restoreBtn, false);
        showToast(error instanceof Error ? error.message : 'Failed to restore contacts', 'error');
    }
}

/**
 * Open purge modal
 */
function openPurgeModal(): void {
    const errorEl = document.getElementById('purge-error')!;
    clearError(errorEl);
    
    document.getElementById('purge-modal')!.style.display = 'flex';
}

/**
 * Confirm and execute purge
 */
async function confirmPurge(): Promise<void> {
    const errorEl = document.getElementById('purge-error')!;
    const confirmBtn = document.getElementById('btn-confirm-purge')! as HTMLButtonElement;
    const daysSelect = document.getElementById('purge-days') as HTMLSelectElement;
    const jewellerSelect = document.getElementById('purge-jeweller') as HTMLSelectElement;

    clearError(errorEl);

    const olderThanDays = parseInt(daysSelect.value);
    const jewellerId = jewellerSelect.value ? parseInt(jewellerSelect.value) : null;

    const confirmText = jewellerId 
        ? `This will PERMANENTLY delete all contacts for jeweller ID ${jewellerId} that were deleted more than ${olderThanDays} days ago. This cannot be undone. Type 'CONFIRM' to proceed.`
        : `This will PERMANENTLY delete ALL contacts across ALL jewellers that were deleted more than ${olderThanDays} days ago. This cannot be undone. Type 'CONFIRM' to proceed.`;

    const userConfirm = prompt(confirmText);
    
    if (userConfirm !== 'CONFIRM') {
        showError(errorEl, 'Purge cancelled');
        return;
    }

    setButtonLoading(confirmBtn, true);

    try {
        const result = await apiRequest<PurgeResponse>(
            '/admin/contacts/purge',
            authService,
            {
                method: 'POST',
                body: JSON.stringify({
                    older_than_days: olderThanDays,
                    jeweller_id: jewellerId
                })
            }
        );

        setButtonLoading(confirmBtn, false);
        document.getElementById('purge-modal')!.style.display = 'none';
        
        showToast(`Successfully purged ${result.purged_count} contacts`, 'success');
        loadDeletedContacts();
    } catch (error) {
        setButtonLoading(confirmBtn, false);
        showError(errorEl, error instanceof Error ? error.message : 'Failed to purge contacts');
    }
}
