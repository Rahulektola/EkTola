/**
 * Jeweller Detail Page
 * View and manage individual jeweller details
 */
import { checkAdminAuth, AdminNavigation, formatDate, formatDateOnly, formatNumber, createStatusBadge, showToast, apiRequest, apiUpload, ConfirmationModal, clearError, showError, setButtonLoading } from './admin-common.js';
const authService = window.authService;
let jewellerId;
let jewellerData = null;
let notesTimeout = null;
// DOM Elements
let loadingState;
let errorState;
let contentContainer;
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
    loadingState = document.getElementById('loading-state');
    errorState = document.getElementById('error-state');
    contentContainer = document.getElementById('content-container');
    setupEventListeners();
    loadJewellerDetails();
});
/**
 * Setup event listeners
 */
function setupEventListeners() {
    var _a, _b, _c, _d, _e, _f, _g, _h;
    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            switchTab(tab);
        });
    });
    // Approval actions
    (_a = document.getElementById('btn-approve')) === null || _a === void 0 ? void 0 : _a.addEventListener('click', approveJeweller);
    (_b = document.getElementById('btn-reject')) === null || _b === void 0 ? void 0 : _b.addEventListener('click', showRejectForm);
    (_c = document.getElementById('btn-confirm-reject')) === null || _c === void 0 ? void 0 : _c.addEventListener('click', confirmReject);
    (_d = document.getElementById('btn-cancel-reject')) === null || _d === void 0 ? void 0 : _d.addEventListener('click', hideRejectForm);
    // Impersonate
    (_e = document.getElementById('btn-impersonate')) === null || _e === void 0 ? void 0 : _e.addEventListener('click', impersonateJeweller);
    // Delete
    (_f = document.getElementById('btn-delete-jeweller')) === null || _f === void 0 ? void 0 : _f.addEventListener('click', deleteJeweller);
    // Admin notes with auto-save
    const notesTextarea = document.getElementById('admin-notes');
    notesTextarea === null || notesTextarea === void 0 ? void 0 : notesTextarea.addEventListener('input', () => {
        if (notesTimeout) {
            clearTimeout(notesTimeout);
        }
        notesTimeout = window.setTimeout(saveAdminNotes, 2000); // Auto-save after 2s
        const status = document.getElementById('notes-save-status');
        status.textContent = 'Typing...';
        status.style.color = '#6b7280';
    });
    // Upload contacts
    (_g = document.getElementById('btn-upload-contacts')) === null || _g === void 0 ? void 0 : _g.addEventListener('click', () => {
        document.getElementById('upload-modal').style.display = 'flex';
    });
    (_h = document.getElementById('btn-upload')) === null || _h === void 0 ? void 0 : _h.addEventListener('click', uploadContacts);
    // Debug contacts - removed in favor of inline segment display
    // document.getElementById('btn-debug-contacts')?.addEventListener('click', showContactsDiagnostics);
}
/**
 * Load jeweller details from API
 */
async function loadJewellerDetails() {
    loadingState.style.display = 'flex';
    errorState.style.display = 'none';
    contentContainer.style.display = 'none';
    try {
        jewellerData = await apiRequest(`/admin/jewellers/${jewellerId}`, authService);
        displayJewellerDetails(jewellerData);
        loadingState.style.display = 'none';
        contentContainer.style.display = 'block';
        // Load contacts for first tab
        loadContacts();
    }
    catch (error) {
        console.error('Failed to load jeweller:', error);
        loadingState.style.display = 'none';
        errorState.style.display = 'block';
        const errorMsg = errorState.querySelector('.error-message');
        errorMsg.textContent = error instanceof Error ? error.message : 'Failed to load jeweller details';
    }
}
/**
 * Display jeweller details in UI
 */
function displayJewellerDetails(jeweller) {
    // Header
    document.getElementById('jeweller-name').textContent = jeweller.business_name;
    document.getElementById('approval-status-badge').innerHTML = createStatusBadge(jeweller.approval_status);
    // Profile
    document.getElementById('profile-business-name').textContent = jeweller.business_name;
    document.getElementById('profile-owner-name').textContent = jeweller.owner_name || '-';
    document.getElementById('profile-phone').textContent = jeweller.phone_number;
    document.getElementById('profile-email').textContent = jeweller.email || '-';
    document.getElementById('profile-address').textContent = jeweller.address || '-';
    document.getElementById('profile-location').textContent = jeweller.location || '-';
    document.getElementById('profile-timezone').textContent = jeweller.timezone;
    document.getElementById('profile-created').textContent = formatDate(jeweller.created_at);
    // Stats
    document.getElementById('stat-contacts').textContent = formatNumber(jeweller.total_contacts);
    document.getElementById('stat-campaigns').textContent = formatNumber(jeweller.total_campaigns);
    document.getElementById('stat-messages').textContent = formatNumber(jeweller.total_messages);
    // Approval section
    const approvalSection = document.getElementById('approval-section');
    if (jeweller.approval_status === 'PENDING') {
        approvalSection.style.display = 'block';
    }
    // WhatsApp Integration
    document.getElementById('meta-waba-id').textContent = jeweller.waba_id || '-';
    document.getElementById('meta-phone-id').textContent = jeweller.phone_number_id || '-';
    document.getElementById('meta-is-whatsapp').textContent = jeweller.is_whatsapp_business ? 'Yes' : 'No';
    document.getElementById('meta-app-status').textContent = jeweller.meta_app_status ? 'Active' : 'Inactive';
    // Admin Notes
    const notesTextarea = document.getElementById('admin-notes');
    notesTextarea.value = jeweller.admin_notes || '';
}
/**
 * Switch between tabs
 */
function switchTab(tab) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tab) {
            btn.classList.add('active');
        }
    });
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tab}`).classList.add('active');
    // Load data for lazy tabs
    if (tab === 'campaigns') {
        loadCampaigns();
    }
    else if (tab === 'messages') {
        loadMessages();
    }
}
/**
 * Load segment distribution
 */
async function loadSegmentDistribution() {
    try {
        const cacheBust = Date.now();
        const data = await apiRequest(`/admin/jewellers/${jewellerId}/contacts/diagnostics?_t=${cacheBust}`, authService);
        console.log('[Segments] Diagnostics data:', data);
        const segmentContainer = document.getElementById('segment-stats');
        if (!data.diagnostics.segment_distribution || data.diagnostics.segment_distribution.length === 0) {
            segmentContainer.innerHTML = '<span style="color: #9ca3af;">No contacts yet</span>';
            return;
        }
        segmentContainer.innerHTML = data.diagnostics.segment_distribution.map((s) => `
            <div style="padding: 0.5rem 1rem; background: white; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                <div style="font-size: 0.75rem; color: #6b7280; text-transform: uppercase;">${s.segment}</div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #111827;">${s.count}</div>
            </div>
        `).join('');
        console.log('[Segments] Successfully rendered segment distribution');
    }
    catch (error) {
        console.error('[Segments] Failed to load:', error);
        document.getElementById('segment-stats').innerHTML = '<span style="color: #ef4444;">Failed to load</span>';
    }
}
/**
 * Load contacts
 */
async function loadContacts() {
    var _a;
    const container = document.getElementById('contacts-list');
    container.innerHTML = '<p>Loading contacts...</p>';
    console.log('[Contacts] Loading contacts for jeweller ID:', jewellerId);
    try {
        // Add cache-busting parameter to force fresh request
        const cacheBust = Date.now();
        const url = `/admin/jewellers/${jewellerId}/contacts?page_size=50&_t=${cacheBust}`;
        console.log('[Contacts] Fetching from:', url);
        const data = await apiRequest(url, authService);
        console.log('[Contacts] API response:', data);
        console.log('[Contacts] Total contacts:', data.total);
        console.log('[Contacts] Contacts array length:', ((_a = data.contacts) === null || _a === void 0 ? void 0 : _a.length) || 0);
        if (!data.contacts || data.contacts.length === 0) {
            const message = data.total > 0
                ? `<p class="info">Total of ${formatNumber(data.total)} contacts found, but none loaded in this batch.</p>`
                : '<p>No contacts found</p>';
            container.innerHTML = message;
            console.log('[Contacts] No contacts to display');
            return;
        }
        console.log('[Contacts] Rendering', data.contacts.length, 'contacts');
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
                    ${data.contacts.slice(0, 10).map((c) => `
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
        console.log('[Contacts] Successfully rendered contacts list');
        // Load segment distribution
        loadSegmentDistribution();
    }
    catch (error) {
        console.error('[Contacts] Failed to load contacts:', error);
        console.error('[Contacts] Error details:', {
            jewellerId,
            error: error instanceof Error ? error.message : String(error),
            stack: error instanceof Error ? error.stack : undefined
        });
        container.innerHTML = `
            <div class="error">
                <p>Failed to load contacts</p>
                <p class="text-muted">${error instanceof Error ? error.message : 'Unknown error'}</p>
                <button class="btn btn-secondary btn-sm" onclick="location.reload()">Retry</button>
            </div>
        `;
    }
}
/**
 * Load campaigns
 */
async function loadCampaigns() {
    const container = document.getElementById('campaigns-list');
    container.innerHTML = '<p>Loading campaigns...</p>';
    try {
        const data = await apiRequest(`/admin/jewellers/${jewellerId}/campaigns?page_size=50`, authService);
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
                    ${data.campaigns.map((c) => `
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
    }
    catch (error) {
        console.error('Failed to load campaigns:', error);
        container.innerHTML = '<p class="error">Failed to load campaigns</p>';
    }
}
/**
 * Load messages
 */
async function loadMessages() {
    const container = document.getElementById('messages-list');
    container.innerHTML = '<p>Loading messages...</p>';
    try {
        const data = await apiRequest(`/admin/jewellers/${jewellerId}/messages?page_size=50`, authService);
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
                    ${data.messages.slice(0, 20).map((m) => `
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
    }
    catch (error) {
        console.error('Failed to load messages:', error);
        container.innerHTML = '<p class="error">Failed to load messages</p>';
    }
}
/**
 * Approve jeweller
 */
async function approveJeweller() {
    const confirmed = await new ConfirmationModal('Approve Jeweller', `Approve ${jewellerData === null || jewellerData === void 0 ? void 0 : jewellerData.business_name}? They will be able to create campaigns and send messages.`, 'Approve', 'Cancel').show();
    if (!confirmed)
        return;
    try {
        await apiRequest(`/admin/jewellers/${jewellerId}/approve`, authService, { method: 'POST' });
        showToast('Jeweller approved successfully', 'success');
        setTimeout(() => location.reload(), 1000);
    }
    catch (error) {
        showToast(error instanceof Error ? error.message : 'Failed to approve', 'error');
    }
}
/**
 * Show reject form
 */
function showRejectForm() {
    document.getElementById('rejection-form').style.display = 'block';
    document.getElementById('btn-reject').style.display = 'none';
    document.getElementById('btn-approve').style.display = 'none';
}
/**
 * Hide reject form
 */
function hideRejectForm() {
    document.getElementById('rejection-form').style.display = 'none';
    document.getElementById('btn-reject').style.display = 'inline-block';
    document.getElementById('btn-approve').style.display = 'inline-block';
    document.getElementById('rejection-reason').value = '';
}
/**
 * Confirm reject
 */
async function confirmReject() {
    const textarea = document.getElementById('rejection-reason');
    const reason = textarea.value.trim();
    const errorEl = document.getElementById('rejection-error');
    if (reason.length < 5) {
        showError(errorEl, 'Rejection reason must be at least 5 characters');
        return;
    }
    clearError(errorEl);
    try {
        await apiRequest(`/admin/jewellers/${jewellerId}/reject`, authService, {
            method: 'POST',
            body: JSON.stringify({ rejection_reason: reason })
        });
        showToast('Jeweller rejected', 'success');
        setTimeout(() => location.reload(), 1000);
    }
    catch (error) {
        showError(errorEl, error instanceof Error ? error.message : 'Failed to reject');
    }
}
/**
 * Save admin notes
 */
async function saveAdminNotes() {
    const textarea = document.getElementById('admin-notes');
    const status = document.getElementById('notes-save-status');
    status.textContent = 'Saving...';
    status.style.color = '#6366f1';
    try {
        await apiRequest(`/admin/jewellers/${jewellerId}/notes`, authService, {
            method: 'PUT',
            body: JSON.stringify({ admin_notes: textarea.value })
        });
        status.textContent = 'Saved';
        status.style.color = '#10b981';
        setTimeout(() => {
            status.textContent = '';
        }, 2000);
    }
    catch (error) {
        console.error('Failed to save notes:', error);
        status.textContent = 'Failed to save';
        status.style.color = '#ef4444';
    }
}
/**
 * Impersonate jeweller
 */
async function impersonateJeweller() {
    const confirmed = await new ConfirmationModal('Impersonate Jeweller', `View dashboard as ${jewellerData === null || jewellerData === void 0 ? void 0 : jewellerData.business_name}?`, 'Continue', 'Cancel').show();
    if (!confirmed)
        return;
    try {
        const result = await authService.impersonateJeweller(jewellerId);
        showToast(`Now viewing as ${result.jeweller_name}`, 'success');
        setTimeout(() => {
            window.location.href = '/dashboard.html';
        }, 1000);
    }
    catch (error) {
        showToast(error instanceof Error ? error.message : 'Impersonation failed', 'error');
    }
}
/**
 * Delete jeweller
 */
async function deleteJeweller() {
    const confirmed = await new ConfirmationModal('Delete Jeweller', `Permanently delete ${jewellerData === null || jewellerData === void 0 ? void 0 : jewellerData.business_name}? This will remove all contacts, campaigns, and messages. This action cannot be undone.`, 'Delete', 'Cancel').show();
    if (!confirmed)
        return;
    try {
        await apiRequest(`/admin/jewellers/${jewellerId}`, authService, { method: 'DELETE' });
        showToast('Jeweller deleted successfully', 'success');
        setTimeout(() => {
            window.location.href = '/admin/jewellers.html';
        }, 1000);
    }
    catch (error) {
        showToast(error instanceof Error ? error.message : 'Failed to delete', 'error');
    }
}
/**
 * Upload contacts
 */
async function uploadContacts() {
    const fileInput = document.getElementById('file-input');
    const errorEl = document.getElementById('upload-error');
    const uploadBtn = document.getElementById('btn-upload');
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
        const result = await apiUpload(`/admin/jewellers/${jewellerId}/contacts/upload`, authService, formData);
        setButtonLoading(uploadBtn, false);
        // Display results
        const resultsEl = document.getElementById('upload-results');
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
                    ${result.failure_details.slice(0, 10).map((f) => `
                        <li>Row ${f.row}: ${f.name} (${f.mobile}) - ${f.reason}</li>
                    `).join('')}
                </ul>
            ` : ''}
        `;
        showToast('Upload completed', 'success');
        // Reload jeweller details to update stat cards and contact list
        await loadJewellerDetails();
    }
    catch (error) {
        setButtonLoading(uploadBtn, false);
        showError(errorEl, error instanceof Error ? error.message : 'Upload failed');
    }
}
/**
 * Show contacts diagnostics information
 */
async function showContactsDiagnostics() {
    console.log('[Diagnostics] Fetching diagnostics for jeweller ID:', jewellerId);
    try {
        // Add cache-busting parameter
        const cacheBust = Date.now();
        const data = await apiRequest(`/admin/jewellers/${jewellerId}/contacts/diagnostics?_t=${cacheBust}`, authService);
        console.log('[Diagnostics] Data received:', data);
        // Display in alert for now (can be improved with modal)
        const diagnosticsInfo = `
=== CONTACT DIAGNOSTICS ===
Jeweller: ${data.jeweller_name} (ID: ${data.jeweller_id})

Total Contacts (All): ${data.diagnostics.total_contacts_all}
Total Contacts (Active): ${data.diagnostics.total_contacts_active}
Total Contacts (Deleted): ${data.diagnostics.total_contacts_deleted}

Segment Distribution:
${data.diagnostics.segment_distribution.map((s) => `  - ${s.segment}: ${s.count}`).join('\n')}

Sample Contacts (Latest 5):
${data.diagnostics.sample_contacts.map((c, idx) => `  ${idx + 1}. ${c.name} (${c.phone_number}) - ${c.segment}`).join('\n')}

API Endpoint: ${data.api_test.endpoint}
        `.trim();
        alert(diagnosticsInfo);
        console.log('[Diagnostics] Full data:', JSON.stringify(data, null, 2));
    }
    catch (error) {
        console.error('[Diagnostics] Failed to fetch diagnostics:', error);
        showToast('Failed to fetch diagnostics', 'error');
    }
}
//# sourceMappingURL=jeweller-detail.js.map