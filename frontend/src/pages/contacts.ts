/**
 * Contacts Page TypeScript Module
 * Handles contact listing, search, filtering, pagination, and CRUD
 */

import { API_BASE } from '@/config/api';
import '@/services/auth';

// ========== Interfaces ==========

interface Contact {
  id: number;
  name: string | null;
  phone_number: string;
  segment: string;
  preferred_language: string;
  opted_out: boolean;
  created_at: string;
  updated_at: string;
}

interface ContactListResponse {
  contacts: Contact[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface ContactSegmentStats {
  segment: string;
  count: number;
  opted_out_count: number;
}

interface ContactData {
  name: string;
  mobile: string;
  purpose: string;
  date: string;
}

// ========== Constants ==========

const SEGMENT_DISPLAY: Record<string, string> = {
  'GOLD_LOAN': 'Gold Loan',
  'GOLD_SIP': 'Gold SIP',
  'BOTH': 'Both (SIP & Loan)',
  'MARKETING': 'Marketing',
};

const SEGMENT_CSS_CLASS: Record<string, string> = {
  'GOLD_LOAN': 'segment-gold-loan',
  'GOLD_SIP': 'segment-gold-sip',
  'BOTH': 'segment-both',
  'MARKETING': 'segment-marketing',
};

const PAGE_SIZE = 50;

// ========== State ==========

let currentPage = 1;
let currentSegmentFilter = '';
let currentSearch = '';
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;
let selectedFile: File | null = null;

// ========== Auth Check ==========

console.log('📋 Contacts page initializing...');

if (!window.authService.isAuthenticated()) {
  console.warn('⚠️ Not authenticated, redirecting to login');
  window.location.href = '/index.html';
}

if (window.authService.accessToken && window.authService.isTokenExpired(window.authService.accessToken)) {
  console.warn('⚠️ Token expired, redirecting to login');
  window.authService.logout();
  window.location.href = '/index.html';
}

// ========== Init ==========

document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  loadContacts();
  loadStats();
});

// ========== Event Listeners ==========

function initEventListeners(): void {
  // Logout
  document.getElementById('logoutBtn')?.addEventListener('click', () => {
    window.authService.logout();
    window.location.href = '/index.html';
  });

  // Search
  const searchInput = document.getElementById('searchInput') as HTMLInputElement;
  searchInput?.addEventListener('input', () => {
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      currentSearch = searchInput.value.trim();
      currentPage = 1;
      loadContacts();
    }, 300);
  });

  // Segment filter
  const segmentFilter = document.getElementById('segmentFilter') as HTMLSelectElement;
  segmentFilter?.addEventListener('change', () => {
    currentSegmentFilter = segmentFilter.value;
    currentPage = 1;
    loadContacts();
  });

  // Add Contact Modal
  document.getElementById('addContactBtn')?.addEventListener('click', openAddModal);
  document.getElementById('closeAddModal')?.addEventListener('click', closeAddModal);
  document.getElementById('cancelAddContact')?.addEventListener('click', closeAddModal);
  document.getElementById('submitAddContact')?.addEventListener('click', submitAddContact);

  // Bulk Upload Modal
  document.getElementById('bulkUploadBtn')?.addEventListener('click', openBulkModal);
  document.getElementById('closeBulkModal')?.addEventListener('click', closeBulkModal);
  document.getElementById('cancelBulkUpload')?.addEventListener('click', closeBulkModal);
  document.getElementById('submitBulkUpload')?.addEventListener('click', submitBulkUpload);

  // File upload
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput') as HTMLInputElement;

  dropZone?.addEventListener('click', () => fileInput?.click());
  fileInput?.addEventListener('change', handleFileSelect);

  dropZone?.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
  dropZone?.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });
  dropZone?.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = (e as DragEvent).dataTransfer?.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
    }
  });

  document.getElementById('clearFileBtn')?.addEventListener('click', clearFile);

  // Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        (overlay as HTMLElement).classList.remove('active');
      }
    });
  });
}

// ========== API Calls ==========

async function loadContacts(): Promise<void> {
  const container = document.getElementById('contactsTableContainer');
  if (!container) return;

  container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

  try {
    const params = new URLSearchParams({
      page: currentPage.toString(),
      page_size: PAGE_SIZE.toString(),
    });

    if (currentSegmentFilter) {
      params.set('segment', currentSegmentFilter);
    }
    if (currentSearch) {
      params.set('search', currentSearch);
    }

    const response = await fetch(`${API_BASE}/contacts/?${params}`, {
      headers: window.authService.getAuthHeaders(),
    });

    if (!response.ok) {
      if (response.status === 401) {
        window.authService.logout();
        window.location.href = '/index.html';
        return;
      }
      throw new Error(`Failed to load contacts: ${response.status}`);
    }

    const data: ContactListResponse = await response.json();
    renderContacts(data);
    renderPagination(data);
  } catch (err) {
    console.error('❌ Error loading contacts:', err);
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <h3>Failed to load contacts</h3>
        <p>${err instanceof Error ? err.message : 'Unknown error'}</p>
        <button class="btn btn-primary" onclick="location.reload()">Retry</button>
      </div>
    `;
  }
}

async function loadStats(): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/contacts/stats`, {
      headers: window.authService.getAuthHeaders(),
    });

    if (!response.ok) return;

    const stats: ContactSegmentStats[] = await response.json();

    let total = 0;
    let goldLoan = 0;
    let goldSip = 0;
    let both = 0;

    for (const stat of stats) {
      total += stat.count;
      if (stat.segment === 'GOLD_LOAN') goldLoan = stat.count;
      else if (stat.segment === 'GOLD_SIP') goldSip = stat.count;
      else if (stat.segment === 'BOTH') both = stat.count;
    }

    setTextContent('statTotal', total.toString());
    setTextContent('statGoldLoan', goldLoan.toString());
    setTextContent('statGoldSip', goldSip.toString());
    setTextContent('statBoth', both.toString());
  } catch (err) {
    console.error('❌ Error loading stats:', err);
  }
}

// ========== Rendering ==========

function renderContacts(data: ContactListResponse): void {
  const container = document.getElementById('contactsTableContainer');
  if (!container) return;

  if (data.contacts.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">👥</div>
        <h3>No contacts found</h3>
        <p>${currentSearch || currentSegmentFilter ? 'Try changing your search or filter.' : 'Add contacts to get started!'}</p>
        ${!currentSearch && !currentSegmentFilter ? '<button class="btn btn-primary" id="emptyAddBtn">➕ Add Your First Contact</button>' : ''}
      </div>
    `;

    document.getElementById('emptyAddBtn')?.addEventListener('click', openAddModal);
    return;
  }

  const tableHtml = `
    <table class="contacts-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Phone</th>
          <th>Segment</th>
        </tr>
      </thead>
      <tbody>
        ${data.contacts.map(contact => `
          <tr>
            <td class="contact-name">${escapeHtml(contact.name || 'N/A')}</td>
            <td class="contact-phone">${escapeHtml(contact.phone_number)}</td>
            <td>
              <span class="segment-badge ${SEGMENT_CSS_CLASS[contact.segment] || 'segment-marketing'}">
                ${SEGMENT_DISPLAY[contact.segment] || contact.segment}
              </span>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;

  container.innerHTML = tableHtml;
}

function renderPagination(data: ContactListResponse): void {
  const paginationContainer = document.getElementById('paginationContainer');
  const paginationInfo = document.getElementById('paginationInfo');
  const paginationControls = document.getElementById('paginationControls');

  if (!paginationContainer || !paginationInfo || !paginationControls) return;

  if (data.total === 0) {
    paginationContainer.style.display = 'none';
    return;
  }

  paginationContainer.style.display = 'flex';

  const start = (data.page - 1) * data.page_size + 1;
  const end = Math.min(data.page * data.page_size, data.total);
  paginationInfo.textContent = `Showing ${start}–${end} of ${data.total} contacts`;

  let controlsHtml = '';

  // Prev button
  controlsHtml += `<button class="page-btn" ${data.page <= 1 ? 'disabled' : ''} data-page="${data.page - 1}">← Prev</button>`;

  // Page numbers
  const maxVisible = 5;
  let startPage = Math.max(1, data.page - Math.floor(maxVisible / 2));
  const endPage = Math.min(data.total_pages, startPage + maxVisible - 1);
  startPage = Math.max(1, endPage - maxVisible + 1);

  if (startPage > 1) {
    controlsHtml += `<button class="page-btn" data-page="1">1</button>`;
    if (startPage > 2) controlsHtml += `<span style="padding: 8px 4px; color: #9ca3af;">...</span>`;
  }

  for (let i = startPage; i <= endPage; i++) {
    controlsHtml += `<button class="page-btn ${i === data.page ? 'active' : ''}" data-page="${i}">${i}</button>`;
  }

  if (endPage < data.total_pages) {
    if (endPage < data.total_pages - 1) controlsHtml += `<span style="padding: 8px 4px; color: #9ca3af;">...</span>`;
    controlsHtml += `<button class="page-btn" data-page="${data.total_pages}">${data.total_pages}</button>`;
  }

  // Next button
  controlsHtml += `<button class="page-btn" ${data.page >= data.total_pages ? 'disabled' : ''} data-page="${data.page + 1}">Next →</button>`;

  paginationControls.innerHTML = controlsHtml;

  // Attach click handlers
  paginationControls.querySelectorAll('.page-btn:not(:disabled)').forEach(btn => {
    btn.addEventListener('click', () => {
      const page = parseInt((btn as HTMLElement).dataset.page || '1', 10);
      if (page !== currentPage) {
        currentPage = page;
        loadContacts();
        // Scroll to top of table
        document.querySelector('.card')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

// ========== Add Contact Modal ==========

function openAddModal(): void {
  document.getElementById('addContactModal')?.classList.add('active');
  const dateInput = document.getElementById('contactDate') as HTMLInputElement;
  if (dateInput) {
    dateInput.valueAsDate = new Date();
  }
}

function closeAddModal(): void {
  document.getElementById('addContactModal')?.classList.remove('active');
  (document.getElementById('addContactForm') as HTMLFormElement)?.reset();
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
    date: (document.getElementById('contactDate') as HTMLInputElement).value,
  };

  const submitBtn = document.getElementById('submitAddContact') as HTMLButtonElement;
  submitBtn.disabled = true;
  submitBtn.textContent = 'Adding...';

  try {
    const response = await fetch(`${API_BASE}/contacts/add-one`, {
      method: 'POST',
      headers: window.authService.getAuthHeaders(),
      body: JSON.stringify(contactData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to add contact');
    }

    closeAddModal();
    alert('✅ Contact added successfully!');
    loadContacts();
    loadStats();
  } catch (err) {
    alert(`❌ ${err instanceof Error ? err.message : 'Failed to add contact'}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Add Contact';
  }
}

// ========== Bulk Upload Modal ==========

function openBulkModal(): void {
  document.getElementById('bulkUploadModal')?.classList.add('active');
}

function closeBulkModal(): void {
  document.getElementById('bulkUploadModal')?.classList.remove('active');
  clearFile();
}

function handleFileSelect(e: Event): void {
  const input = e.target as HTMLInputElement;
  if (input.files && input.files.length > 0) {
    setSelectedFile(input.files[0]);
  }
}

function setSelectedFile(file: File): void {
  const validExtensions = ['.csv', '.xlsx', '.xls'];
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

  if (!validExtensions.includes(ext)) {
    alert('Please select a CSV or Excel file.');
    return;
  }

  selectedFile = file;

  const fileSelectedEl = document.getElementById('fileSelected');
  if (fileSelectedEl) {
    fileSelectedEl.classList.add('show');
  }

  setTextContent('fileName', file.name);
  setTextContent('fileSize', formatFileSize(file.size));

  const uploadBtn = document.getElementById('submitBulkUpload') as HTMLButtonElement;
  if (uploadBtn) uploadBtn.disabled = false;
}

function clearFile(): void {
  selectedFile = null;
  const fileSelectedEl = document.getElementById('fileSelected');
  if (fileSelectedEl) fileSelectedEl.classList.remove('show');

  const fileInput = document.getElementById('fileInput') as HTMLInputElement;
  if (fileInput) fileInput.value = '';

  const uploadBtn = document.getElementById('submitBulkUpload') as HTMLButtonElement;
  if (uploadBtn) uploadBtn.disabled = true;
}

async function submitBulkUpload(): Promise<void> {
  if (!selectedFile) {
    alert('Please select a file first.');
    return;
  }

  const submitBtn = document.getElementById('submitBulkUpload') as HTMLButtonElement;
  submitBtn.disabled = true;
  submitBtn.textContent = 'Uploading...';

  try {
    const formData = new FormData();
    formData.append('file', selectedFile);

    // Need headers without Content-Type (browser sets multipart boundary)
    const token = window.authService.accessToken;
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/contacts/bulk-upload-dashboard`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    const result = await response.json();

    closeBulkModal();
    alert(`✅ Upload complete!\n\nImported: ${result.imported}\nUpdated: ${result.updated}\nFailed: ${result.failed}\nTotal rows: ${result.total_rows}`);
    loadContacts();
    loadStats();
  } catch (err) {
    alert(`❌ ${err instanceof Error ? err.message : 'Upload failed'}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Upload Contacts';
  }
}

// ========== Utilities ==========

function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function setTextContent(id: string, text: string): void {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}
