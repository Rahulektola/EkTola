/**
 * Dashboard TypeScript Module
 * Handles dashboard functionality, contact management, and UI updates
 */

import type { AuthService } from './auth.js';

interface ContactData {
  name: string;
  mobile: string;
  purpose: string;
  date: string;
}

interface DashboardData {
  total_contacts?: number;
  opted_out_contacts?: number;
  active_campaigns?: number;
  total_messages_sent?: number;
  recent_delivery_rate?: number;
  recent_read_rate?: number;
  recent_campaign_runs?: CampaignRun[];
  contact_distribution?: ContactDistribution[];
}

interface CampaignRun {
  campaign_name?: string;
  campaign_type?: string;
  sub_segment?: string;
  status?: string;
  total_queued?: number;
  total_sent?: number;
  total_delivered?: number;
  total_read?: number;
  total_failed?: number;
}

interface ContactDistribution {
  segment: string;
  count: number;
  languages?: string[];
}

interface JewellerProfile {
  business_name: string;
  phone_number: string;
}

declare global {
  interface Window {
    AuthService: typeof AuthService;
    authService: AuthService;
    loadDashboard: () => Promise<void>;
    submitAddContact: () => Promise<void>;
    openAddOneModal: () => void;
    closeAddOneModal: () => void;
    openBulkUploadModal: () => void;
    closeBulkUploadModal: () => void;
    handleFileSelect: (event: Event) => void;
    clearFile: () => void;
    submitBulkUpload: () => Promise<void>;
    openAdminPermissionModal: () => void;
    closeAdminPermissionModal: () => void;
    grantAdminPermission: () => void;
  }
}

// This export makes the file a module, enabling global augmentation
export {};

let selectedFile: File | null = null;

// Auth check
console.log('🔐 Dashboard initializing...');
console.log('✓ Is authenticated:', window.authService.isAuthenticated());

if (!window.authService.isAuthenticated()) {
  console.warn('⚠️ Not authenticated, redirecting to login');
  window.location.href = '/index.html';
}

// Dashboard Functions
async function loadDashboard(): Promise<void> {
  try {
    console.log('📊 Loading dashboard data...');
    const response = await fetch('http://localhost:8000/analytics/dashboard', {
      headers: window.authService.getAuthHeaders()
    });

    if (!response.ok) {
      console.error('❌ Dashboard load failed:', response.status);
      throw new Error('Failed to load dashboard');
    }

    const data: DashboardData = await response.json();
    console.log('✅ Dashboard data loaded:', data);
    updateUI(data);
  } catch (error) {
    console.error('❌ Error loading dashboard:', error);
    alert('Failed to load dashboard data');
  }
}

function updateUI(data: DashboardData): void {
  const elements = {
    totalContacts: document.getElementById('totalContacts'),
    optedOut: document.getElementById('optedOut'),
    activeCampaigns: document.getElementById('activeCampaigns'),
    messagesSent: document.getElementById('messagesSent'),
    deliveryRate: document.getElementById('deliveryRate'),
    readRate: document.getElementById('readRate')
  };

  if (elements.totalContacts) elements.totalContacts.textContent = String(data.total_contacts || 0);
  if (elements.optedOut) elements.optedOut.textContent = String(data.opted_out_contacts || 0);
  if (elements.activeCampaigns) elements.activeCampaigns.textContent = String(data.active_campaigns || 0);
  if (elements.messagesSent) elements.messagesSent.textContent = String(data.total_messages_sent || 0);
  if (elements.deliveryRate) elements.deliveryRate.textContent = (data.recent_delivery_rate || 0).toFixed(1);
  if (elements.readRate) elements.readRate.textContent = (data.recent_read_rate || 0).toFixed(1);

  loadJewellerProfile();
  updateCampaigns(data.recent_campaign_runs || []);
  updateDistribution(data.contact_distribution || []);
}

async function loadJewellerProfile(): Promise<void> {
  try {
    const response = await fetch('http://localhost:8000/auth/me/jeweller', {
      headers: window.authService.getAuthHeaders()
    });

    if (response.ok) {
      const jeweller: JewellerProfile = await response.json();
      const businessNameEl = document.getElementById('businessName');
      if (businessNameEl) {
        businessNameEl.textContent = jeweller.business_name;
      }
      console.log('✅ Profile loaded:', jeweller.business_name);
    }
  } catch (error) {
    console.error('❌ Error loading profile:', error);
  }
}

function updateCampaigns(campaigns: CampaignRun[]): void {
  const container = document.getElementById('campaignsList');
  if (!container) return;

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

function updateDistribution(distribution: ContactDistribution[]): void {
  const container = document.getElementById('contactDistribution');
  if (!container) return;

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
function openAddOneModal(): void {
  document.getElementById('addOneModal')?.classList.add('active');
  const dateInput = document.getElementById('contactDate') as HTMLInputElement;
  if (dateInput) {
    dateInput.valueAsDate = new Date();
  }
}

function closeAddOneModal(): void {
  document.getElementById('addOneModal')?.classList.remove('active');
  const form = document.getElementById('addContactForm') as HTMLFormElement;
  form?.reset();
}

async function submitAddContact(): Promise<void> {
  const form = document.getElementById('addContactForm') as HTMLFormElement;
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  const contactData: ContactData = {
    name: (document.getElementById('contactName') as HTMLInputElement).value,
    mobile: (document.getElementById('contactMobile') as HTMLInputElement).value,
    purpose: (document.getElementById('contactPurpose') as HTMLSelectElement).value,
    date: (document.getElementById('contactDate') as HTMLInputElement).value
  };

  console.log('📝 Submitting contact:', contactData);

  try {
    if (!window.authService) {
      console.error('❌ authService not found');
      alert('Authentication error. Please refresh the page and login again.');
      return;
    }

    if (!window.authService.accessToken) {
      console.error('❌ No access token found');
      alert('Session expired. Please login again.');
      window.location.href = '/index.html';
      return;
    }

    console.log('✓ Auth token exists');

    const response = await fetch('http://localhost:8000/contacts/add-one', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${window.authService.accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(contactData)
    });

    console.log('📡 Response status:', response.status);

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
  } catch (error) {
    console.error('❌ Error adding contact:', error);
    alert(`Failed to add contact:\n${(error as Error).message}`);
  }
}

// Modal Functions - Bulk Upload
function openBulkUploadModal(): void {
  document.getElementById('bulkUploadModal')?.classList.add('active');
}

function closeBulkUploadModal(): void {
  document.getElementById('bulkUploadModal')?.classList.remove('active');
  clearFile();
}

function handleFileSelect(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
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
    const uploadBtn = document.getElementById('uploadBtn') as HTMLButtonElement;

    if (fileNameEl) fileNameEl.textContent = file.name;
    if (fileSizeEl) fileSizeEl.textContent = formatFileSize(file.size);
    fileSelectedEl?.classList.add('show');
    if (uploadBtn) uploadBtn.disabled = false;
  }
}

function clearFile(): void {
  selectedFile = null;
  const fileInput = document.getElementById('fileInput') as HTMLInputElement;
  const fileSelectedEl = document.getElementById('fileSelected');
  const uploadBtn = document.getElementById('uploadBtn') as HTMLButtonElement;

  if (fileInput) fileInput.value = '';
  fileSelectedEl?.classList.remove('show');
  if (uploadBtn) uploadBtn.disabled = true;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function submitBulkUpload(): Promise<void> {
  if (!selectedFile) {
    alert('Please select a file first');
    return;
  }

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const uploadBtn = document.getElementById('uploadBtn') as HTMLButtonElement;
    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Uploading...';

    const response = await fetch('http://localhost:8000/contacts/bulk-upload-dashboard', {
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
    
    let message = `Upload completed!\n\n`;
    message += `Total rows: ${result.total_rows}\n`;
    message += `✓ Imported: ${result.imported}\n`;
    message += `↻ Updated: ${result.updated}\n`;
    message += `✗ Failed: ${result.failed}\n`;
    
    if (result.failed > 0 && result.failure_details.length > 0) {
      message += `\nFirst few failures:\n`;
      result.failure_details.slice(0, 3).forEach((f: any) => {
        message += `Row ${f.row}: ${f.name} - ${f.reason}\n`;
      });
    }
    
    alert(message);
    closeBulkUploadModal();
    loadDashboard();
  } catch (error) {
    console.error('Error uploading file:', error);
    alert((error as Error).message || 'Failed to upload contacts. Please try again.');
  } finally {
    const uploadBtn = document.getElementById('uploadBtn') as HTMLButtonElement;
    uploadBtn.disabled = false;
    uploadBtn.textContent = 'Upload Contacts';
  }
}

// Admin Permission Modal
function openAdminPermissionModal(): void {
  document.getElementById('adminPermissionModal')?.classList.add('active');
}

function closeAdminPermissionModal(): void {
  document.getElementById('adminPermissionModal')?.classList.remove('active');
}

function grantAdminPermission(): void {
  alert('Admin permission feature coming soon!');
  closeAdminPermissionModal();
}

// Drag and drop functionality
const dropZone = document.getElementById('dropZone');
if (dropZone) {
  dropZone.addEventListener('dragover', (e: DragEvent) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', (e: DragEvent) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      const fileInput = document.getElementById('fileInput') as HTMLInputElement;
      fileInput.files = files;
      handleFileSelect({ target: fileInput } as any);
    }
  });
}

// Modal click outside to close
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', (e: Event) => {
    if (e.target === overlay) {
      overlay.classList.remove('active');
    }
  });
});

// Logout
document.getElementById('logoutBtn')?.addEventListener('click', () => {
  window.authService.logout();
  window.location.href = '/index.html';
});

// Profile
document.getElementById('profileBtn')?.addEventListener('click', () => {
  alert('Profile page coming soon!');
});

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

// Load on page load
loadDashboard();
