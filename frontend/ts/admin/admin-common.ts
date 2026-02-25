/**
 * Admin Common Utilities
 * Shared functions and components for admin dashboard pages
 */

import { AuthService } from '../auth.js';

const baseURL = '/api';

/**
 * Check if user is authenticated as admin
 * Redirects to admin login if not authenticated or not admin
 */
export function checkAdminAuth(authService: AuthService): boolean {
    if (!authService.isAuthenticated()) {
        window.location.href = '/admin-login.html';
        return false;
    }

    const decoded = authService.decodeToken(authService.accessToken!);
    if (!decoded?.is_admin) {
        authService.logout();
        window.location.href = '/admin-login.html';
        return false;
    }

    return true;
}

/**
 * Get required DOM element with type safety
 */
export function getElement<T extends HTMLElement>(id: string): T {
    const element = document.getElementById(id) as T;
    if (!element) {
        throw new Error(`Element with id "${id}" not found`);
    }
    return element;
}

/**
 * Format ISO date string to readable format
 */
export function formatDate(isoString: string | null): string {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-IN', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format date to date only (no time)
 */
export function formatDateOnly(isoString: string | null): string {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-IN', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric'
    });
}

/**
 * Format percentage for display
 */
export function formatPercentage(value: number | null): string {
    if (value === null || value === undefined) return '0%';
    return `${value.toFixed(1)}%`;
}

/**
 * Format large numbers with commas
 */
export function formatNumber(value: number): string {
    return new Intl.NumberFormat('en-IN').format(value);
}

/**
 * Show toast notification
 */
export function showToast(message: string, type: 'success' | 'error' | 'info' = 'success'): void {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        color: white;
        font-weight: 500;
        z-index: 9999;
        animation: slideIn 0.3s ease-out;
        max-width: 400px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;

    if (type === 'success') {
        toast.style.background = '#10b981';
    } else if (type === 'error') {
        toast.style.background = '#ef4444';
    } else {
        toast.style.background = '#6366f1';
    }

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Show error message in element
 */
export function showError(element: HTMLElement | null, message: string): void {
    if (!element) return;
    element.textContent = message;
    element.style.display = 'block';
}

/**
 * Clear error message
 */
export function clearError(element: HTMLElement | null): void {
    if (!element) return;
    element.textContent = '';
    element.style.display = 'none';
}

/**
 * Set loading state on button
 */
export function setButtonLoading(button: HTMLButtonElement, isLoading: boolean, originalText?: string): void {
    if (isLoading) {
        button.dataset.originalText = button.textContent || '';
        button.disabled = true;
        button.innerHTML = '<span class="btn-loader"></span> Loading...';
    } else {
        button.disabled = false;
        button.textContent = originalText || button.dataset.originalText || 'Submit';
    }
}

/**
 * Create status badge HTML
 */
export function createStatusBadge(status: string): string {
    const statusLower = status.toLowerCase();
    let className = 'status-badge';
    
    if (statusLower === 'approved' || statusLower === 'active' || statusLower === 'delivered' || statusLower === 'read') {
        className += ' status-success';
    } else if (statusLower === 'pending' || statusLower === 'queued' || statusLower === 'sent') {
        className += ' status-warning';
    } else if (statusLower === 'rejected' || statusLower === 'failed' || statusLower === 'paused') {
        className += ' status-error';
    } else if (statusLower === 'draft') {
        className += ' status-draft';
    }

    return `<span class="${className}">${status}</span>`;
}

/**
 * Confirmation Modal
 */
export class ConfirmationModal {
    private overlay: HTMLDivElement;
    private modal: HTMLDivElement;
    private onConfirm: () => void;
    private onCancel: () => void;

    constructor(title: string, message: string, confirmText: string = 'Confirm', cancelText: string = 'Cancel') {
        this.onConfirm = () => {};
        this.onCancel = () => {};

        // Create overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'modal-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9998;
        `;

        // Create modal
        this.modal = document.createElement('div');
        this.modal.className = 'confirmation-modal';
        this.modal.style.cssText = `
            background: white;
            border-radius: 0.5rem;
            padding: 1.5rem;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        `;

        this.modal.innerHTML = `
            <h3 style="margin: 0 0 1rem; font-size: 1.25rem; color: #1f2937;">${title}</h3>
            <p style="margin: 0 0 1.5rem; color: #6b7280;">${message}</p>
            <div style="display: flex; gap: 0.75rem; justify-content: flex-end;">
                <button id="modal-cancel" class="btn btn-secondary">${cancelText}</button>
                <button id="modal-confirm" class="btn btn-admin">${confirmText}</button>
            </div>
        `;

        this.overlay.appendChild(this.modal);

        // Setup event listeners
        const cancelBtn = this.modal.querySelector('#modal-cancel') as HTMLButtonElement;
        const confirmBtn = this.modal.querySelector('#modal-confirm') as HTMLButtonElement;

        cancelBtn.addEventListener('click', () => {
            this.close();
            this.onCancel();
        });

        confirmBtn.addEventListener('click', () => {
            this.close();
            this.onConfirm();
        });

        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.close();
                this.onCancel();
            }
        });
    }

    show(): Promise<boolean> {
        return new Promise((resolve) => {
            this.onConfirm = () => resolve(true);
            this.onCancel = () => resolve(false);
            document.body.appendChild(this.overlay);
        });
    }

    close(): void {
        this.overlay.remove();
    }
}

/**
 * Pagination Component
 */
export class PaginationControls {
    private container: HTMLElement;
    private currentPage: number;
    private pageSize: number;
    private total: number;
    private onPageChange: (page: number, pageSize: number) => void;

    constructor(
        containerId: string,
        initialPage: number,
        pageSize: number,
        total: number,
        onPageChange: (page: number, pageSize: number) => void
    ) {
        this.container = getElement(containerId);
        this.currentPage = initialPage;
        this.pageSize = pageSize;
        this.total = total;
        this.onPageChange = onPageChange;
        this.render();
    }

    update(page: number, pageSize: number, total: number): void {
        this.currentPage = page;
        this.pageSize = pageSize;
        this.total = total;
        this.render();
    }

    private render(): void {
        const totalPages = Math.ceil(this.total / this.pageSize);
        const startItem = (this.currentPage - 1) * this.pageSize + 1;
        const endItem = Math.min(this.currentPage * this.pageSize, this.total);

        this.container.innerHTML = `
            <div class="pagination">
                <div class="pagination-info">
                    Showing ${startItem}-${endItem} of ${formatNumber(this.total)}
                </div>
                <div class="pagination-controls">
                    <button 
                        id="prev-page" 
                        class="btn btn-secondary btn-sm" 
                        ${this.currentPage === 1 ? 'disabled' : ''}
                    >
                        Previous
                    </button>
                    <span class="pagination-pages">
                        Page ${this.currentPage} of ${totalPages}
                    </span>
                    <button 
                        id="next-page" 
                        class="btn btn-secondary btn-sm"
                        ${this.currentPage >= totalPages ? 'disabled' : ''}
                    >
                        Next
                    </button>
                </div>
                <div class="pagination-size">
                    <label for="page-size">Per page:</label>
                    <select id="page-size" class="form-select">
                        <option value="20" ${this.pageSize === 20 ? 'selected' : ''}>20</option>
                        <option value="50" ${this.pageSize === 50 ? 'selected' : ''}>50</option>
                        <option value="100" ${this.pageSize === 100 ? 'selected' : ''}>100</option>
                    </select>
                </div>
            </div>
        `;

        // Event listeners
        const prevBtn = this.container.querySelector('#prev-page') as HTMLButtonElement;
        const nextBtn = this.container.querySelector('#next-page') as HTMLButtonElement;
        const pageSizeSelect = this.container.querySelector('#page-size') as HTMLSelectElement;

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.currentPage > 1) {
                    this.onPageChange(this.currentPage - 1, this.pageSize);
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (this.currentPage < totalPages) {
                    this.onPageChange(this.currentPage + 1, this.pageSize);
                }
            });
        }

        if (pageSizeSelect) {
            pageSizeSelect.addEventListener('change', () => {
                const newPageSize = parseInt(pageSizeSelect.value);
                this.onPageChange(1, newPageSize); // Reset to page 1 when changing page size
            });
        }
    }
}

/**
 * Admin Navigation Component
 */
export class AdminNavigation {
    private container: HTMLElement;
    private activePage: string;

    constructor(containerId: string, activePage: string) {
        this.container = getElement(containerId);
        this.activePage = activePage;
        this.render();
    }

    private render(): void {
        this.container.innerHTML = `
            <div class="admin-sidebar">
                <div class="admin-logo">
                    <h2>ekTola Admin</h2>
                </div>
                <nav class="admin-nav">
                    <a href="/admin/dashboard.html" class="admin-nav-item ${this.activePage === 'dashboard' ? 'active' : ''}">
                        <span class="nav-icon">📊</span>
                        Dashboard
                    </a>
                    <a href="/admin/jewellers.html" class="admin-nav-item ${this.activePage === 'jewellers' ? 'active' : ''}">
                        <span class="nav-icon">👥</span>
                        Jewellers
                    </a>
                    <a href="/admin/analytics.html" class="admin-nav-item ${this.activePage === 'analytics' ? 'active' : ''}">
                        <span class="nav-icon">📈</span>
                        Analytics
                    </a>
                </nav>
                <div class="admin-nav-footer">
                    <button id="admin-logout" class="btn btn-secondary btn-block">
                        Logout
                    </button>
                </div>
            </div>
        `;

        // Setup logout
        const logoutBtn = this.container.querySelector('#admin-logout') as HTMLButtonElement;
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                const authService = (window as any).authService as AuthService;
                authService.logout();
                window.location.href = '/admin-login.html';
            });
        }
    }
}

/**
 * API request helper with error handling
 */
export async function apiRequest<T>(
    endpoint: string,
    authService: AuthService,
    options: RequestInit = {}
): Promise<T> {
    const url = `${baseURL}${endpoint}`;
    
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            ...authService.getAuthHeaders(),
            ...options.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `Request failed with status ${response.status}`);
    }

    return response.json();
}

/**
 * API request for file upload
 */
export async function apiUpload<T>(
    endpoint: string,
    authService: AuthService,
    formData: FormData
): Promise<T> {
    const url = `${baseURL}${endpoint}`;
    
    // Get auth headers but exclude Content-Type for file uploads
    // Browser will automatically set Content-Type with multipart boundary
    const authHeaders = authService.getAuthHeaders();
    const headers: HeadersInit = {};
    
    // Only include Authorization header, not Content-Type
    if (authHeaders && typeof authHeaders === 'object' && 'Authorization' in authHeaders) {
        headers['Authorization'] = (authHeaders as Record<string, string>)['Authorization'];
    }
    
    const response = await fetch(url, {
        method: 'POST',
        headers: headers,
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
        
        // Handle detail being an object or array (FastAPI validation errors)
        let errorMessage: string;
        if (typeof error.detail === 'string') {
            errorMessage = error.detail;
        } else if (Array.isArray(error.detail)) {
            // FastAPI validation errors return an array of error objects
            errorMessage = error.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
        } else if (error.detail && typeof error.detail === 'object') {
            errorMessage = JSON.stringify(error.detail);
        } else {
            errorMessage = `Upload failed with status ${response.status}`;
        }
        
        throw new Error(errorMessage);
    }

    return response.json();
}
