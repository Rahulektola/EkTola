/**
 * Jeweller Detail Page
 * View and manage individual jeweller details
 */

import { AuthService } from '../auth.js';
import {
    checkAdminAuth,
    AdminNavigation,
    formatDate,
    formatDateOnly,
    formatNumber,
    createStatusBadge,
    showToast,
    apiRequest,
    apiUpload,
    ConfirmationModal,
    clearError,
    showError,
    setButtonLoading
} from './admin-common.js';

const authService = (window as any).authService as AuthService;

interface JewellerDetail {
    id: number;
    business_name: string;
    owner_name: string | null;
    phone_number: string;
    address: string | null;
    location: string | null;
    waba_id: string | null;
    phone_number_id: string | null;
    is_whatsapp_business: boolean;
    meta_app_status: boolean;
    approval_status: string;
    rejection_reason: string | null;
    approved_at: string | null;
    is_active: boolean;
    admin_notes: string | null;
    timezone: string;
    created_at: string;
    total_contacts: number;
    total_campaigns: number;
    total_messages: number;
    email: string | null;
}

let jewellerId: number;
let jewellerData: JewellerDetail | null = null;
let notesTimeout: number | null = null;

// DOM Elements
let loadingState: HTMLElement;
let errorState: HTMLElement;
let contentContainer: HTMLElement;

document.addEventListener('DOMContentLoaded', () => {
    if (!checkAdminAuth(authService)) {
        return;
    }

    new AdminNavigation('admin-nav-container', 'jewellers');

    // Get jeweller ID from URL
    const params = new URLSearchParams(window.location.search);
    const idParam = params.get('id');

    if (!idParam) {
        window.location.href = '/admin/jewellers.html';
        return;
    }

    jewellerId = parseInt(idParam);

    loadingState = document.getElementById('loading-state')!;
    errorState = document.getElementById('error-state')!;
    contentContainer = document.getElementById('content-container')!;

    setupEventListeners();
    loadJewellerDetails();
});

/**
 * Setup event listeners
 */
function setupEventListeners(): void {
    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = (btn as HTMLElement).dataset.tab!;
            switchTab(tab);
        });
    });

    // Approval actions
    document.getElementById('btn-approve')?.addEventListener('click', approveJeweller);
    document.getElementById('btn-reject')?.addEventListener('click', showRejectForm);
    document.getElementById('btn-confirm-reject')?.addEventListener('click', confirmReject);
    document.getElementById('btn-cancel-reject')?.addEventListener('click', hideRejectForm);

    // Impersonate
    document.getElementById('btn-impersonate')?.addEventListener('click', impersonateJeweller);

    // Delete
    document.getElementById('btn-delete-jeweller')?.addEventListener('click', deleteJeweller);

    // Admin notes with auto-save
    const notesTextarea = document.getElementById('admin-notes') as HTMLTextAreaElement;
    notesTextarea?.addEventListener('input', () => {
        if (notesTimeout) {
            clearTimeout(notesTimeout);
        }
        notesTimeout = window.setTimeout(saveAdminNotes, 2000); // Auto-save after 2s
        
        const status = document.getElementById('notes-save-status')!;
        status.textContent = 'Typing...';
        status.style.color = '#6b7280';
    });

    // Upload contacts
    document.getElementById('btn-upload-contacts')?.addEventListener('click', () => {
        document.getElementById('upload-modal')!.style.display = 'flex';
    });

    document.getElementById('btn-upload')?.addEventListener('click', uploadContacts);
}

/**
 * Load jeweller details from API
 */
async function loadJewellerDetails(): Promise<void> {
    loadingState.style.display = 'flex';
    errorState.style.display = 'none';
    contentContainer.style.display = 'none';

    try {
        jewellerData = await apiRequest<JewellerDetail>(
            `/admin/jewellers/${jewellerId}`,
            authService
        );

        displayJewellerDetails(jewellerData);
        
        loadingState.style.display = 'none';
        contentContainer.style.display = 'block';

        // Load contacts for first tab
        loadContacts();
    } catch (error) {
        console.error('Failed to load jeweller:', error);
        loadingState.style.display = 'none';
        errorState.style.display = 'block';
        const errorMsg = errorState.querySelector('.error-message') as HTMLElement;
        errorMsg.textContent = error instanceof Error ? error.message : 'Failed to load jeweller details';
    }
}

/**
 * Display jeweller details in UI
 */
function displayJewellerDetails(jeweller: JewellerDetail): void {
    // Header
    document.getElementById('jeweller-name')!.textContent = jeweller.business_name;
    document.getElementById('approval-status-badge')!.innerHTML = createStatusBadge(jeweller.approval_status);

    // Profile
    document.getElementById('profile-business-name')!.textContent = jeweller.business_name;
    document.getElementById('profile-owner-name')!.textContent = jeweller.owner_name || '-';
    document.getElementById('profile-phone')!.textContent = jeweller.phone_number;
    document.getElementById('profile-email')!.textContent = jeweller.email || '-';
    document.getElementById('profile-address')!.textContent = jeweller.address || '-';
    document.getElementById('profile-location')!.textContent = jeweller.location || '-';
    document.getElementById('profile-timezone')!.textContent = jeweller.timezone;
    document.getElementById('profile-created')!.textContent = formatDate(jeweller.created_at);

    // Stats
    document.getElementById('stat-contacts')!.textContent = formatNumber(jeweller.total_contacts);
    document.getElementById('stat-campaigns')!.textContent = formatNumber(jeweller.total_campaigns);
    document.getElementById('stat-messages')!.textContent = formatNumber(jeweller.total_messages);

    // Approval section
    const approvalSection = document.getElementById('approval-section')!;
    if (jeweller.approval_status === 'PENDING') {
        approvalSection.style.display = 'block';
    }

    // WhatsApp Integration
    document.getElementById('meta-waba-id')!.textContent = jeweller.waba_id || '-';
    document.getElementById('meta-phone-id')!.textContent = jeweller.phone_number_id || '-';
    document.getElementById('meta-is-whatsapp')!.textContent = jeweller.is_whatsapp_business ? 'Yes' : 'No';
    document.getElementById('meta-app-status')!.textContent = jeweller.meta_app_status ? 'Active' : 'Inactive';

    // Admin Notes
    const notesTextarea = document.getElementById('admin-notes') as HTMLTextAreaElement;
    notesTextarea.value = jeweller.admin_notes || '';
}

/**
 * Switch between tabs
 */
function switchTab(tab: string): void {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if ((btn as HTMLElement).dataset.tab === tab) {
            btn.classList.add('active');
        }
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tab}`)!.classList.add('active');

    // Load data for lazy tabs
    if (tab === 'campaigns') {
        loadCampaigns();
    } else if (tab === 'messages') {
        loadMessages();
    }
}

/**
 * Load contacts
 */
async function loadContacts(): Promise<void> {
    const container = document.getElementById('contacts-list')!;
    container.innerHTML = '<p>Loading contacts...</p>';

    try {
        const data = await apiRequest<any>(
            `/admin/jewellers/${jewellerId}/contacts?page_size=50`,
            authService
        );

        if (data.contacts.length === 0) {
            container.innerHTML = '<p>No contacts found</p>';
            return;
        }

        container.innerHTML = `
            <p>Total: ${formatNumber(data.total)} contacts</p>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Phone</th>
                        <th>Segment</th>
                        <th>Language</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.contacts.slice(0, 10).map((c: any) => `
                        <tr>
                            <td>${c.name || '-'}</td>
                            <td>${c.phone_number}</td>
                            <td>${createStatusBadge(c.segment)}</td>
                            <td>${c.preferred_language}</td>
                            <td>${formatDateOnly(c.created_at)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            ${data.total > 10 ? `<p class="text-muted">Showing first 10 of ${formatNumber(data.total)} contacts</p>` : ''}
        `;
    } catch (error) {
        console.error('Failed to load contacts:', error);
        container.innerHTML = '<p class="error">Failed to load contacts</p>';
    }
}

/**
 * Load campaigns
 */
async function loadCampaigns(): Promise<void> {
    const container = document.getElementById('campaigns-list')!;
    container.innerHTML = '<p>Loading campaigns...</p>';

    try {
        const data = await apiRequest<any>(
            `/admin/jewellers/${jewellerId}/campaigns?page_size=50`,
            authService
        );

        if (data.campaigns.length === 0) {
            container.innerHTML = '<p>No campaigns found</p>';
            return;
        }

        container.innerHTML = `
            <p>Total: ${formatNumber(data.total)} campaigns</p>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Messages Sent</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.campaigns.map((c: any) => `
                        <tr>
                            <td>${c.name}</td>
                            <td>${createStatusBadge(c.campaign_type)}</td>
                            <td>${createStatusBadge(c.status)}</td>
                            <td>${formatNumber(c.total_messages_sent)}</td>
                            <td>${formatDateOnly(c.created_at)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (error) {
        console.error('Failed to load campaigns:', error);
        container.innerHTML = '<p class="error">Failed to load campaigns</p>';
    }
}

/**
 * Load messages
 */
async function loadMessages(): Promise<void> {
    const container = document.getElementById('messages-list')!;
    container.innerHTML = '<p>Loading messages...</p>';

    try {
        const data = await apiRequest<any>(
            `/admin/jewellers/${jewellerId}/messages?page_size=50`,
            authService
        );

        if (data.messages.length === 0) {
            container.innerHTML = '<p>No messages found</p>';
            return;
        }

        container.innerHTML = `
            <p>Total: ${formatNumber(data.total)} messages</p>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Phone</th>
                        <th>Template</th>
                        <th>Status</th>
                        <th>Sent At</th>
                        <th>Delivered At</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.messages.slice(0, 20).map((m: any) => `
                        <tr>
                            <td>${m.phone_number}</td>
                            <td>${m.template_name}</td>
                            <td>${createStatusBadge(m.status)}</td>
                            <td>${formatDate(m.sent_at)}</td>
                            <td>${formatDate(m.delivered_at)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            ${data.total > 20 ? `<p class="text-muted">Showing first 20 of ${formatNumber(data.total)} messages</p>` : ''}
        `;
    } catch (error) {
        console.error('Failed to load messages:', error);
        container.innerHTML = '<p class="error">Failed to load messages</p>';
    }
}

/**
 * Approve jeweller
 */
async function approveJeweller(): Promise<void> {
    const confirmed = await new ConfirmationModal(
        'Approve Jeweller',
        `Approve ${jewellerData?.business_name}? They will be able to create campaigns and send messages.`,
        'Approve',
        'Cancel'
    ).show();

    if (!confirmed) return;

    try {
        await apiRequest(
            `/admin/jewellers/${jewellerId}/approve`,
            authService,
            { method: 'POST' }
        );

        showToast('Jeweller approved successfully', 'success');
        setTimeout(() => location.reload(), 1000);
    } catch (error) {
        showToast(error instanceof Error ? error.message : 'Failed to approve', 'error');
    }
}

/**
 * Show reject form
 */
function showRejectForm(): void {
    document.getElementById('rejection-form')!.style.display = 'block';
    document.getElementById('btn-reject')!.style.display = 'none';
    document.getElementById('btn-approve')!.style.display = 'none';
}

/**
 * Hide reject form
 */
function hideRejectForm(): void {
    document.getElementById('rejection-form')!.style.display = 'none';
    document.getElementById('btn-reject')!.style.display = 'inline-block';
    document.getElementById('btn-approve')!.style.display = 'inline-block';
    (document.getElementById('rejection-reason') as HTMLTextAreaElement).value = '';
}

/**
 * Confirm reject
 */
async function confirmReject(): Promise<void> {
    const textarea = document.getElementById('rejection-reason') as HTMLTextAreaElement;
    const reason = textarea.value.trim();
    const errorEl = document.getElementById('rejection-error')!;

    if (reason.length < 5) {
        showError(errorEl, 'Rejection reason must be at least 5 characters');
        return;
    }

    clearError(errorEl);

    try {
        await apiRequest(
            `/admin/jewellers/${jewellerId}/reject`,
            authService,
            {
                method: 'POST',
                body: JSON.stringify({ rejection_reason: reason })
            }
        );

        showToast('Jeweller rejected', 'success');
        setTimeout(() => location.reload(), 1000);
    } catch (error) {
        showError(errorEl, error instanceof Error ? error.message : 'Failed to reject');
    }
}

/**
 * Save admin notes
 */
async function saveAdminNotes(): Promise<void> {
    const textarea = document.getElementById('admin-notes') as HTMLTextAreaElement;
    const status = document.getElementById('notes-save-status')!;

    status.textContent = 'Saving...';
    status.style.color = '#6366f1';

    try {
        await apiRequest(
            `/admin/jewellers/${jewellerId}/notes`,
            authService,
            {
                method: 'PUT',
                body: JSON.stringify({ admin_notes: textarea.value })
            }
        );

        status.textContent = 'Saved';
        status.style.color = '#10b981';
        
        setTimeout(() => {
            status.textContent = '';
        }, 2000);
    } catch (error) {
        console.error('Failed to save notes:', error);
        status.textContent = 'Failed to save';
        status.style.color = '#ef4444';
    }
}

/**
 * Impersonate jeweller
 */
async function impersonateJeweller(): Promise<void> {
    const confirmed = await new ConfirmationModal(
        'Impersonate Jeweller',
        `View dashboard as ${jewellerData?.business_name}?`,
        'Continue',
        'Cancel'
    ).show();

    if (!confirmed) return;

    try {
        const result = await authService.impersonateJeweller(jewellerId);
        showToast(`Now viewing as ${result.jeweller_name}`, 'success');
        
        setTimeout(() => {
            window.location.href = '/dashboard.html';
        }, 1000);
    } catch (error) {
        showToast(error instanceof Error ? error.message : 'Impersonation failed', 'error');
    }
}

/**
 * Delete jeweller
 */
async function deleteJeweller(): Promise<void> {
    const confirmed = await new ConfirmationModal(
        'Delete Jeweller',
        `Permanently delete ${jewellerData?.business_name}? This will remove all contacts, campaigns, and messages. This action cannot be undone.`,
        'Delete',
        'Cancel'
    ).show();

    if (!confirmed) return;

    try {
        await apiRequest(
            `/admin/jewellers/${jewellerId}`,
            authService,
            { method: 'DELETE' }
        );

        showToast('Jeweller deleted successfully', 'success');
        setTimeout(() => {
            window.location.href = '/admin/jewellers.html';
        }, 1000);
    } catch (error) {
        showToast(error instanceof Error ? error.message : 'Failed to delete', 'error');
    }
}

/**
 * Upload contacts
 */
async function uploadContacts(): Promise<void> {
    const fileInput = document.getElementById('file-input') as HTMLInputElement;
    const errorEl = document.getElementById('upload-error')!;
    const uploadBtn = document.getElementById('btn-upload') as HTMLButtonElement;

    clearError(errorEl);

    if (!fileInput.files || fileInput.files.length === 0) {
        showError(errorEl, 'Please select a file');
        return;
    }

    const file = fileInput.files[0];

    setButtonLoading(uploadBtn, true);

    try {
        const formData = new FormData();
        formData.append('file', file);

        const result = await apiUpload<any>(
            `/admin/jewellers/${jewellerId}/contacts/upload`,
            authService,
            formData
        );

        setButtonLoading(uploadBtn, false);

        // Display results
        const resultsEl = document.getElementById('upload-results')!;
        resultsEl.style.display = 'block';
        resultsEl.innerHTML = `
            <h4>Upload Results</h4>
            <p><strong>Total Rows:</strong> ${result.total_rows}</p>
            <p><strong>Imported:</strong> ${result.imported}</p>
            <p><strong>Updated:</strong> ${result.updated}</p>
            <p><strong>Failed:</strong> ${result.failed}</p>
            ${result.failure_details && result.failure_details.length > 0 ? `
                <h5>Failures:</h5>
                <ul>
                    ${result.failure_details.slice(0, 10).map((f: any) => `
                        <li>Row ${f.row}: ${f.name} (${f.mobile}) - ${f.reason}</li>
                    `).join('')}
                </ul>
            ` : ''}
        `;

        showToast('Upload completed', 'success');
        loadContacts(); // Reload contacts list
    } catch (error) {
        setButtonLoading(uploadBtn, false);
        showError(errorEl, error instanceof Error ? error.message : 'Upload failed');
    }
}
