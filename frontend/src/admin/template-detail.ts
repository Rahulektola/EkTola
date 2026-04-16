/**
 * Admin Template Detail Page
 * Shows full details + action buttons for a single template
 */

import '@/services/auth';
import {
    checkAdminAuth,
    AdminNavigation,
    formatDateOnly,
    createStatusBadge,
    showToast,
    apiRequest,
} from '@/admin/common';
import type { AuthService } from '@/services/auth';

const authService = window.authService as AuthService;

// ─── Types ────────────────────────────────────────────────────────────────────

interface TemplateTranslation {
    id: number;
    language: string;
    body_text: string;
    header_text: string | null;
    footer_text: string | null;
    whatsapp_template_id: string | null;
    approval_status: string;
    created_at: string;
}

interface Template {
    id: number;
    template_name: string;
    display_name: string;
    campaign_type: string;
    sub_segment: string | null;
    description: string | null;
    category: string;
    is_active: boolean;
    variable_count: number;
    variable_names: string | null;
    translations: TemplateTranslation[];
    created_at: string;
    updated_at: string;
}

interface TranslationPreview {
    id: number;
    language: string;
    header_text: string | null;
    body_text: string;
    footer_text: string | null;
    approval_status: string;
    example_header: string | null;
    example_body: string;
    example_footer: string | null;
}

interface TemplatePreviewResponse {
    id: number;
    template_name: string;
    display_name: string;
    campaign_type: string;
    category: string;
    variable_count: number;
    variable_names: string | null;
    dummy_values: Record<string, string>;
    translations: TranslationPreview[];
}

// ─── State ────────────────────────────────────────────────────────────────────

let templateId: number;
let template: Template;

const LANG_LABELS: Record<string, string> = {
    en: 'English', hi: 'Hindi', kn: 'Kannada',
    mr: 'Marathi', ta: 'Tamil', pa: 'Punjabi',
};

function langLabel(code: string): string {
    return LANG_LABELS[code] ?? code.toUpperCase();
}

function escapeHtml(str: string): string {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    if (!checkAdminAuth(authService)) return;
    new AdminNavigation('admin-nav-container', 'templates');

    const params = new URLSearchParams(window.location.search);
    const idParam = params.get('id');
    if (!idParam || isNaN(Number(idParam))) {
        showError('No template ID specified.');
        return;
    }
    templateId = Number(idParam);

    setupModals();
    loadTemplate();
});

// ─── Load & Render ────────────────────────────────────────────────────────────

async function loadTemplate(): Promise<void> {
    try {
        const data = await apiRequest<{ templates: Template[]; total: number }>(
            '/templates/admin/all',
            authService
        );
        const found = (data.templates ?? (data as unknown as Template[])).find(
            (t: Template) => t.id === templateId
        );
        if (!found) { showError('Template not found.'); return; }
        template = found;
        renderPage();
    } catch (e) {
        showError(`Failed to load template: ${(e as Error).message}`);
    }
}

function renderPage(): void {
    document.getElementById('loadingState')!.style.display = 'none';
    document.getElementById('mainContent')!.style.display = '';
    document.title = `${template.display_name} — Template Detail`;

    (document.getElementById('templateDisplayName') as HTMLElement).textContent = template.display_name;
    (document.getElementById('templateName') as HTMLElement).textContent = template.template_name;
    (document.getElementById('page-subtitle') as HTMLElement).textContent = `ID: ${template.id}`;

    const overallStatus = template.translations[0]?.approval_status ?? 'PENDING';
    document.getElementById('templateStatusBadge')!.innerHTML = createStatusBadge(overallStatus);

    // Meta info
    const vars = template.variable_names
        ? template.variable_names.split(',').map(v => `<code style="background:#f3f4f6;padding:2px 6px;border-radius:4px;font-size:12px;">${escapeHtml(v.trim())}</code>`).join(' ')
        : '—';

    document.getElementById('metaGrid')!.innerHTML = `
        <div class="meta-item">
            <span class="meta-label">Type</span>
            <span class="meta-value">${escapeHtml(template.campaign_type)}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Category</span>
            <span class="meta-value">${escapeHtml(template.category)}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Active</span>
            <span class="meta-value">${template.is_active ? '✅ Yes' : '❌ No'}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Variables</span>
            <span class="meta-value">${template.variable_count} &nbsp; ${vars}</span>
        </div>
        ${template.sub_segment ? `<div class="meta-item"><span class="meta-label">Sub Segment</span><span class="meta-value">${escapeHtml(template.sub_segment)}</span></div>` : ''}
        ${template.description ? `<div class="meta-item"><span class="meta-label">Description</span><span class="meta-value">${escapeHtml(template.description)}</span></div>` : ''}
        <div class="meta-item">
            <span class="meta-label">Created</span>
            <span class="meta-value">${formatDateOnly(template.created_at)}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Updated</span>
            <span class="meta-value">${formatDateOnly(template.updated_at)}</span>
        </div>
    `;

    // Translations
    const listEl = document.getElementById('translationsList')!;
    if (template.translations.length === 0) {
        listEl.innerHTML = '<p style="color:#6b7280;">No translations yet.</p>';
    } else {
        listEl.innerHTML = template.translations.map(tr => `
            <div class="translation-card">
                <div class="translation-header">
                    <strong style="font-size:14px;">${escapeHtml(langLabel(tr.language))}</strong>
                    <span>${createStatusBadge(tr.approval_status)}</span>
                </div>
                ${tr.header_text ? `<div style="font-size:12px;color:#6b7280;margin-bottom:6px;"><strong>Header:</strong> ${escapeHtml(tr.header_text)}</div>` : ''}
                <div class="wa-bubble">
                    ${tr.header_text ? `<div class="wa-bubble-header">${escapeHtml(tr.header_text)}</div>` : ''}
                    <div>${escapeHtml(tr.body_text)}</div>
                    ${tr.footer_text ? `<div class="wa-bubble-footer">${escapeHtml(tr.footer_text)}</div>` : ''}
                </div>
                ${tr.whatsapp_template_id ? `<div style="margin-top:8px;font-size:11px;color:#9ca3af;">WA ID: ${escapeHtml(tr.whatsapp_template_id)}</div>` : ''}
            </div>
        `).join('');
    }
}

function showError(msg: string): void {
    document.getElementById('loadingState')!.style.display = 'none';
    const err = document.getElementById('errorState')!;
    err.textContent = msg;
    err.style.display = '';
}

// ─── Modals Setup ─────────────────────────────────────────────────────────────

function setupModals(): void {
    // Preview
    document.getElementById('btnPreview')!.addEventListener('click', openPreview);
    const previewModal = document.getElementById('previewModal')!;
    document.getElementById('previewModalCloseBtn')!.addEventListener('click', () => { previewModal.style.display = 'none'; });
    document.getElementById('previewModalDoneBtn')!.addEventListener('click', () => { previewModal.style.display = 'none'; });
    previewModal.addEventListener('click', (e) => { if (e.target === previewModal) previewModal.style.display = 'none'; });

    // Edit
    document.getElementById('btnEdit')!.addEventListener('click', openEdit);
    const editModal = document.getElementById('editModal')!;
    document.getElementById('editModalCloseBtn')!.addEventListener('click', () => { editModal.style.display = 'none'; });
    document.getElementById('editModalCancelBtn')!.addEventListener('click', () => { editModal.style.display = 'none'; });
    document.getElementById('editModalSaveBtn')!.addEventListener('click', saveEdit);
    editModal.addEventListener('click', (e) => { if (e.target === editModal) editModal.style.display = 'none'; });

    // Sync
    document.getElementById('btnSync')!.addEventListener('click', doSync);

    // Status
    document.getElementById('btnStatus')!.addEventListener('click', openStatus);
    const statusModal = document.getElementById('statusModal')!;
    document.getElementById('statusModalCloseBtn')!.addEventListener('click', () => { statusModal.style.display = 'none'; });
    statusModal.addEventListener('click', (e) => { if (e.target === statusModal) statusModal.style.display = 'none'; });

    // Delete
    document.getElementById('btnDelete')!.addEventListener('click', openDelete);
    const deleteModal = document.getElementById('deleteModal')!;
    document.getElementById('deleteModalCancelBtn')!.addEventListener('click', () => { deleteModal.style.display = 'none'; });
    document.getElementById('deleteModalConfirmBtn')!.addEventListener('click', doDelete);
    deleteModal.addEventListener('click', (e) => { if (e.target === deleteModal) deleteModal.style.display = 'none'; });
}

// ─── Preview ──────────────────────────────────────────────────────────────────

async function openPreview(): Promise<void> {
    const modal = document.getElementById('previewModal')!;
    const title = document.getElementById('previewModalTitle')!;
    const body = document.getElementById('previewModalBody')!;
    title.textContent = 'Loading…';
    body.innerHTML = '<p style="padding:1rem;color:#6b7280;">Loading preview…</p>';
    modal.style.display = 'flex';

    try {
        const data = await apiRequest<TemplatePreviewResponse>(
            `/templates/admin/${templateId}/preview`,
            authService
        );
        title.textContent = data.display_name;
        renderPreview(data, body);
    } catch (e) {
        body.innerHTML = `<p style="color:#ef4444;padding:1rem;">${escapeHtml((e as Error).message)}</p>`;
    }
}

function renderPreview(data: TemplatePreviewResponse, container: HTMLElement): void {
    const translations = data.translations;
    if (translations.length === 0) {
        container.innerHTML = '<p style="color:#6b7280;padding:1rem;">No translations available.</p>';
        return;
    }

    const langTabsHtml = translations.length > 1
        ? `<div class="lang-tabs">${translations.map((t, i) =>
            `<button class="lang-tab-btn${i === 0 ? ' active' : ''}" data-idx="${i}">${langLabel(t.language)} <small>(${t.approval_status})</small></button>`
          ).join('')}</div>`
        : '';

    const panels = translations.map((t, i) => `
        <div class="tpanel" data-panel="${i}" style="${i > 0 ? 'display:none;' : ''}">
            <div class="wa-bubble">
                ${t.example_header ? `<div class="wa-bubble-header">${escapeHtml(t.example_header)}</div>` : ''}
                <div>${escapeHtml(t.example_body)}</div>
                ${t.example_footer ? `<div class="wa-bubble-footer">${escapeHtml(t.example_footer)}</div>` : ''}
            </div>
        </div>`).join('');

    const dummyEntries = Object.entries(data.dummy_values ?? {});
    const varsHtml = dummyEntries.length > 0
        ? `<div class="preview-vars">
               <h4>Variable Mapping</h4>
               ${dummyEntries.map(([n, v]) =>
                   `<span class="var-chip"><span class="vn">${escapeHtml(n)}</span><span class="va">→</span><span class="vv">${escapeHtml(v)}</span></span>`
               ).join('')}
           </div>`
        : '';

    container.innerHTML = `<div style="padding:0 1rem 1rem;">${langTabsHtml}${panels}${varsHtml}</div>`;

    container.querySelectorAll('.lang-tab-btn').forEach(tab => {
        tab.addEventListener('click', () => {
            container.querySelectorAll('.lang-tab-btn').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const idx = (tab as HTMLElement).dataset.idx;
            container.querySelectorAll('.tpanel').forEach(p => {
                (p as HTMLElement).style.display = (p as HTMLElement).dataset.panel === idx ? '' : 'none';
            });
        });
    });
}

// ─── Edit ─────────────────────────────────────────────────────────────────────

function openEdit(): void {
    (document.getElementById('editDisplayName') as HTMLInputElement).value = template.display_name;
    (document.getElementById('editDescription') as HTMLInputElement).value = template.description ?? '';
    (document.getElementById('editIsActive') as HTMLInputElement).checked = template.is_active;
    document.getElementById('editFormError')!.style.display = 'none';
    document.getElementById('editModal')!.style.display = 'flex';
}

async function saveEdit(): Promise<void> {
    const saveBtn = document.getElementById('editModalSaveBtn') as HTMLButtonElement;
    const displayName = (document.getElementById('editDisplayName') as HTMLInputElement).value.trim();
    const description = (document.getElementById('editDescription') as HTMLInputElement).value.trim();
    const isActive = (document.getElementById('editIsActive') as HTMLInputElement).checked;
    const errEl = document.getElementById('editFormError')!;

    if (!displayName) {
        errEl.textContent = 'Display name is required.';
        errEl.style.display = '';
        return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';
    errEl.style.display = 'none';

    try {
        await apiRequest(`/templates/admin/${templateId}`, authService, {
            method: 'PATCH',
            body: JSON.stringify({ display_name: displayName, description: description || undefined, is_active: isActive }),
        });
        document.getElementById('editModal')!.style.display = 'none';
        showToast('Template updated.', 'success');
        await loadTemplate();
    } catch (e) {
        errEl.textContent = (e as Error).message;
        errEl.style.display = '';
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Changes';
    }
}

// ─── Sync ─────────────────────────────────────────────────────────────────────

async function doSync(): Promise<void> {
    const btn = document.getElementById('btnSync') as HTMLButtonElement;
    btn.disabled = true;
    btn.textContent = 'Syncing…';
    try {
        await apiRequest(`/templates/admin/${templateId}/sync-to-whatsapp`, authService, { method: 'POST' });
        showToast('Template submitted to WhatsApp for approval.', 'success');
        await loadTemplate();
    } catch (e) {
        showToast(`Sync failed: ${(e as Error).message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="icon">🔄</span> Sync';
    }
}

// ─── Status ───────────────────────────────────────────────────────────────────

async function openStatus(): Promise<void> {
    const modal = document.getElementById('statusModal')!;
    const box = document.getElementById('statusJsonBox')!;
    box.textContent = 'Loading…';
    modal.style.display = 'flex';
    try {
        const data = await apiRequest<Record<string, unknown>>(
            `/templates/admin/${templateId}/whatsapp-status`,
            authService
        );
        box.textContent = JSON.stringify(data, null, 2);
    } catch (e) {
        box.textContent = `Error: ${(e as Error).message}`;
    }
}

// ─── Delete ───────────────────────────────────────────────────────────────────

function openDelete(): void {
    document.getElementById('deleteModalMsg')!.textContent =
        `Are you sure you want to delete "${template.display_name}"? This cannot be undone.`;
    document.getElementById('deleteModal')!.style.display = 'flex';
}

async function doDelete(): Promise<void> {
    const btn = document.getElementById('deleteModalConfirmBtn') as HTMLButtonElement;
    btn.disabled = true;
    btn.textContent = 'Deleting…';
    try {
        await apiRequest(`/templates/admin/${templateId}`, authService, { method: 'DELETE' });
        showToast('Template deleted.', 'success');
        setTimeout(() => { window.location.href = '/admin/templates.html'; }, 800);
    } catch (e) {
        showToast(`Delete failed: ${(e as Error).message}`, 'error');
        btn.disabled = false;
        btn.textContent = 'Delete';
        document.getElementById('deleteModal')!.style.display = 'none';
    }
}
