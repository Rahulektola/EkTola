/**
 * Dashboard TypeScript Module
 * Handles dashboard functionality, contact management, and UI updates
 */
var _a, _b;
let selectedFile = null;
// Auth check
console.log('🔐 Dashboard initializing...');
console.log('✓ Is authenticated:', window.authService.isAuthenticated());
if (!window.authService.isAuthenticated()) {
    console.warn('⚠️ Not authenticated, redirecting to login');
    window.location.href = '/index.html';
}
// Dashboard Functions
async function loadDashboard() {
    try {
        console.log('📊 Loading dashboard data...');
        const response = await fetch('/api/analytics/dashboard', {
            headers: window.authService.getAuthHeaders()
        });
        if (!response.ok) {
            console.error('❌ Dashboard load failed:', response.status);
            throw new Error('Failed to load dashboard');
        }
        const data = await response.json();
        console.log('✅ Dashboard data loaded:', data);
        updateUI(data);
    }
    catch (error) {
        console.error('❌ Error loading dashboard:', error);
        alert('Failed to load dashboard data');
    }
}
function updateUI(data) {
    console.log('🔄 updateUI called with data:', data);
    console.log('📊 total_contacts value:', data.total_contacts);
    const elements = {
        totalContacts: document.getElementById('totalContacts'),
        optedOut: document.getElementById('optedOut'),
        activeCampaigns: document.getElementById('activeCampaigns'),
        messagesSent: document.getElementById('messagesSent'),
        deliveryRate: document.getElementById('deliveryRate'),
        readRate: document.getElementById('readRate')
    };
    if (elements.totalContacts) {
        console.log('✓ Setting totalContacts to:', data.total_contacts || 0);
        elements.totalContacts.textContent = String(data.total_contacts || 0);
    }
    else {
        console.error('❌ totalContacts element not found!');
    }
    if (elements.optedOut)
        elements.optedOut.textContent = String(data.opted_out_contacts || 0);
    if (elements.activeCampaigns)
        elements.activeCampaigns.textContent = String(data.active_campaigns || 0);
    if (elements.messagesSent)
        elements.messagesSent.textContent = String(data.total_messages_sent || 0);
    if (elements.deliveryRate)
        elements.deliveryRate.textContent = (data.recent_delivery_rate || 0).toFixed(1);
    if (elements.readRate)
        elements.readRate.textContent = (data.recent_read_rate || 0).toFixed(1);
    loadJewellerProfile();
    updateCampaigns(data.recent_campaign_runs || []);
    updateDistribution(data.contact_distribution || []);
}
async function loadJewellerProfile() {
    try {
        const response = await fetch('/api/auth/me/jeweller', {
            headers: window.authService.getAuthHeaders()
        });
        if (response.ok) {
            const jeweller = await response.json();
            const businessNameEl = document.getElementById('businessName');
            if (businessNameEl) {
                businessNameEl.textContent = jeweller.business_name;
            }
            console.log('✅ Profile loaded:', jeweller.business_name);
        }
    }
    catch (error) {
        console.error('❌ Error loading profile:', error);
    }
}
function updateCampaigns(campaigns) {
    const container = document.getElementById('campaignsList');
    if (!container)
        return;
    if (campaigns.length === 0) {
        container.innerHTML = `
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"></rect>
          <line x1="9" y1="9" x2="15" y2="9"></line>
          <line x1="9" y1="15" x2="15" y2="15"></line>
        </svg>
        <p>No campaigns yet. Create your first campaign!</p>
      </div>
    `;
        return;
    }
    container.innerHTML = campaigns.slice(0, 5).map(c => `
    <div class="campaign-item">
      <div class="campaign-header">
        <div>
          <div class="campaign-name">${c.campaign_name || 'Untitled Campaign'}</div>
          <div class="campaign-type">
            ${c.campaign_type === 'UTILITY' ? '🔔 Utility' : '📢 Marketing'}
            ${c.sub_segment ? ' • ' + c.sub_segment.replace('_', ' ') : ''}
          </div>
        </div>
        <span class="status-badge status-${(c.status || 'draft').toLowerCase()}">
          ${c.status || 'Draft'}
        </span>
      </div>
      <div class="campaign-metrics">
        <div class="metric">
          <div class="metric-value">${c.total_queued || 0}</div>
          <div class="metric-label">Queued</div>
        </div>
        <div class="metric">
          <div class="metric-value">${c.total_sent || 0}</div>
          <div class="metric-label">Sent</div>
        </div>
        <div class="metric">
          <div class="metric-value">${c.total_delivered || 0}</div>
          <div class="metric-label">Delivered</div>
        </div>
        <div class="metric">
          <div class="metric-value">${c.total_read || 0}</div>
          <div class="metric-label">Read</div>
        </div>
        <div class="metric">
          <div class="metric-value">${c.total_failed || 0}</div>
          <div class="metric-label">Failed</div>
        </div>
      </div>
    </div>
  `).join('');
}
function updateDistribution(distribution) {
    const container = document.getElementById('contactDistribution');
    if (!container)
        return;
    if (distribution.length === 0) {
        container.innerHTML = `
      <div class="empty-state">
        <p>No contacts yet. Upload contacts to get started!</p>
      </div>
    `;
        return;
    }
    container.innerHTML = distribution.map(item => `
    <div class="distribution-item">
      <div class="dist-info">
        <h4>${item.segment}</h4>
        <div class="dist-languages">
          ${item.languages ? item.languages.join(', ') : 'All languages'}
        </div>
      </div>
      <div class="dist-count">${item.count}</div>
    </div>
  `).join('');
}
// Modal Functions - Add One by One
function openAddOneModal() {
    var _a;
    (_a = document.getElementById('addOneModal')) === null || _a === void 0 ? void 0 : _a.classList.add('active');
    const dateInput = document.getElementById('contactDate');
    if (dateInput) {
        dateInput.valueAsDate = new Date();
    }
}
function closeAddOneModal() {
    var _a;
    (_a = document.getElementById('addOneModal')) === null || _a === void 0 ? void 0 : _a.classList.remove('active');
    const form = document.getElementById('addContactForm');
    form === null || form === void 0 ? void 0 : form.reset();
}
async function submitAddContact() {
    const form = document.getElementById('addContactForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    const contactData = {
        name: document.getElementById('contactName').value,
        mobile: document.getElementById('contactMobile').value,
        purpose: document.getElementById('contactPurpose').value,
        date: document.getElementById('contactDate').value
    };
    console.log('📝 Submitting contact:', contactData);
    try {
        if (!window.authService) {
            console.error('❌ authService not found');
            alert('Authentication error. Please refresh the page and login again.');
            return;
        }
        const token = window.authService.accessToken;
        if (!token) {
            console.error('❌ No access token found');
            alert('Session expired. Please login again.');
            window.location.href = '/index.html';
            return;
        }
        // Check if token is expired
        if (window.authService.isTokenExpired(token)) {
            console.error('❌ Access token has expired');
            alert('Your session has expired. Please login again.');
            window.authService.logout();
            window.location.href = '/index.html';
            return;
        }
        console.log('✓ Auth token exists and is valid');
        const response = await fetch('/api/contacts/add-one', {
            method: 'POST',
            headers: window.authService.getAuthHeaders(),
            body: JSON.stringify(contactData)
        });
        console.log('📡 Response status:', response.status);
        if (response.status === 401) {
            console.error('❌ Unauthorized - token may be invalid');
            alert('Session expired. Please login again.');
            window.authService.logout();
            window.location.href = '/index.html';
            return;
        }
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || `Server error: ${response.status}`;
            console.error('❌ Server error:', errorData);
            throw new Error(errorMessage);
        }
        const result = await response.json();
        console.log('✅ Contact added:', result);
        alert(`✓ Contact "${result.name}" added successfully!\n\nMobile: ${result.mobile}\nPurpose: ${result.purpose}`);
        closeAddOneModal();
        loadDashboard();
    }
    catch (error) {
        console.error('❌ Error adding contact:', error);
        alert(`Failed to add contact:\n${error.message}`);
    }
}
// Modal Functions - Bulk Upload
function openBulkUploadModal() {
    var _a;
    (_a = document.getElementById('bulkUploadModal')) === null || _a === void 0 ? void 0 : _a.classList.add('active');
}
function closeBulkUploadModal() {
    var _a;
    (_a = document.getElementById('bulkUploadModal')) === null || _a === void 0 ? void 0 : _a.classList.remove('active');
    clearFile();
}
function handleFileSelect(event) {
    var _a;
    const input = event.target;
    const file = (_a = input.files) === null || _a === void 0 ? void 0 : _a[0];
    if (file) {
        const validTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
        if (!validTypes.includes(file.type) && !file.name.match(/\.(csv|xlsx|xls)$/i)) {
            alert('Please select a valid CSV or Excel file');
            return;
        }
        selectedFile = file;
        const fileNameEl = document.getElementById('fileName');
        const fileSizeEl = document.getElementById('fileSize');
        const fileSelectedEl = document.getElementById('fileSelected');
        const uploadBtn = document.getElementById('uploadBtn');
        if (fileNameEl)
            fileNameEl.textContent = file.name;
        if (fileSizeEl)
            fileSizeEl.textContent = formatFileSize(file.size);
        fileSelectedEl === null || fileSelectedEl === void 0 ? void 0 : fileSelectedEl.classList.add('show');
        if (uploadBtn)
            uploadBtn.disabled = false;
    }
}
function clearFile() {
    selectedFile = null;
    const fileInput = document.getElementById('fileInput');
    const fileSelectedEl = document.getElementById('fileSelected');
    const uploadBtn = document.getElementById('uploadBtn');
    if (fileInput)
        fileInput.value = '';
    fileSelectedEl === null || fileSelectedEl === void 0 ? void 0 : fileSelectedEl.classList.remove('show');
    if (uploadBtn)
        uploadBtn.disabled = true;
}
function formatFileSize(bytes) {
    if (bytes < 1024)
        return bytes + ' B';
    if (bytes < 1024 * 1024)
        return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
async function submitBulkUpload() {
    if (!selectedFile) {
        alert('Please select a file first');
        return;
    }
    const formData = new FormData();
    formData.append('file', selectedFile);
    try {
        const uploadBtn = document.getElementById('uploadBtn');
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading...';
        const response = await fetch('/api/contacts/bulk-upload-dashboard', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${window.authService.accessToken}`
            },
            body: formData
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        const result = await response.json();
        // Simple success message
        const totalAdded = result.imported + result.updated;
        let message = `✅ ${totalAdded} contact${totalAdded !== 1 ? 's' : ''} added successfully!`;
        // Only show failures if any
        if (result.failed > 0) {
            message += `\n\n⚠️ ${result.failed} contact${result.failed !== 1 ? 's' : ''} could not be added.`;
            if (result.failure_details && result.failure_details.length > 0) {
                message += `\n\nFirst error: ${result.failure_details[0].name} - ${result.failure_details[0].reason}`;
            }
        }
        alert(message);
        closeBulkUploadModal();
        loadDashboard();
    }
    catch (error) {
        console.error('Error uploading file:', error);
        alert(error.message || 'Failed to upload contacts. Please try again.');
    }
    finally {
        const uploadBtn = document.getElementById('uploadBtn');
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload Contacts';
    }
}
// Admin Permission Modal
function openAdminPermissionModal() {
    var _a;
    (_a = document.getElementById('adminPermissionModal')) === null || _a === void 0 ? void 0 : _a.classList.add('active');
}
function closeAdminPermissionModal() {
    var _a;
    (_a = document.getElementById('adminPermissionModal')) === null || _a === void 0 ? void 0 : _a.classList.remove('active');
}
function grantAdminPermission() {
    alert('Admin permission feature coming soon!');
    closeAdminPermissionModal();
}
// Drag and drop functionality
const dropZone = document.getElementById('dropZone');
if (dropZone) {
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    dropZone.addEventListener('drop', (e) => {
        var _a;
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const files = (_a = e.dataTransfer) === null || _a === void 0 ? void 0 : _a.files;
        if (files && files.length > 0) {
            const fileInput = document.getElementById('fileInput');
            fileInput.files = files;
            handleFileSelect({ target: fileInput });
        }
    });
}
// Modal click outside to close
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.classList.remove('active');
        }
    });
});
// Logout
(_a = document.getElementById('logoutBtn')) === null || _a === void 0 ? void 0 : _a.addEventListener('click', () => {
    window.authService.logout();
    window.location.href = '/index.html';
});
// Profile
(_b = document.getElementById('profileBtn')) === null || _b === void 0 ? void 0 : _b.addEventListener('click', () => {
    alert('Profile page coming soon!');
});
// Impersonation Banner
function setupImpersonationBanner() {
    const banner = document.getElementById('impersonation-banner');
    const exitBtn = document.getElementById('exit-impersonation');
    const jewellerNameSpan = document.getElementById('impersonation-text');
    if (!banner || !exitBtn || !jewellerNameSpan) {
        console.log('⚠️ Impersonation banner elements not found');
        return;
    }
    if (window.authService.isImpersonating()) {
        const jeweller = window.authService.getImpersonatedJewellerInfo();
        console.log('👁️ Admin is impersonating:', jeweller);
        if (jeweller) {
            jewellerNameSpan.textContent = `Viewing as ${jeweller.name}`;
            banner.style.display = 'block';
        }
        exitBtn.addEventListener('click', () => {
            console.log('🚪 Exiting impersonation mode');
            window.authService.exitImpersonation();
            window.location.href = '/admin/dashboard.html';
        });
    }
    else {
        banner.style.display = 'none';
    }
}
// Make functions globally available
window.loadDashboard = loadDashboard;
window.submitAddContact = submitAddContact;
window.openAddOneModal = openAddOneModal;
window.closeAddOneModal = closeAddOneModal;
window.openBulkUploadModal = openBulkUploadModal;
window.closeBulkUploadModal = closeBulkUploadModal;
window.handleFileSelect = handleFileSelect;
window.clearFile = clearFile;
window.submitBulkUpload = submitBulkUpload;
window.openAdminPermissionModal = openAdminPermissionModal;
window.closeAdminPermissionModal = closeAdminPermissionModal;
window.grantAdminPermission = grantAdminPermission;
// Initialize on page load
setupImpersonationBanner();
loadDashboard();
export {};
//# sourceMappingURL=dashboard.js.map