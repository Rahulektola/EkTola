/**
 * Admin Template Management
 * Full CRUD for WhatsApp message templates
 */

import '@/services/auth';
import {
    checkAdminAuth,
    AdminNavigation,
    formatDateOnly,
    createStatusBadge,
    showToast,
    apiRequest,
    ConfirmationModal,
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
}

interface TranslationPreview {
    id: number;
    template_id: number;
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
    sub_segment: string | null;
    description: string | null;
    category: string;
    variable_count: number;
    variable_names: string | null;
    dummy_values: Record<string, string>;
    translations: TranslationPreview[];
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

interface TemplateListResponse {
    templates: Template[];
    total: number;
}

interface TemplateCreatePayload {
    template_name: string;
    display_name: string;
    campaign_type: string;
    category: string;
    sub_segment?: string;
    description?: string;
    variable_count: number;
    variable_names?: string[];
    translations: Array<{
        language: string;
        body_text: string;
        header_text?: string;
        footer_text?: string;
    }>;
}

interface TemplateUpdatePayload {
    display_name?: string;
    description?: string;
    is_active?: boolean;
}

// ─── State ────────────────────────────────────────────────────────────────────

let allTemplates: Template[] = [];
let currentFilter = 'all';

// ─── DOM References ───────────────────────────────────────────────────────────

let templatesTable: HTMLTableSectionElement;

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    if (!checkAdminAuth(authService)) return;

    new AdminNavigation('admin-nav-container', 'templates');

    templatesTable = document.getElementById('templates-table') as HTMLTableSectionElement;

    setupFilterTabs();
    setupCreateModal();
    setupStatusModal();
    setupSyncButton();
    setupPreviewModal();

    loadTemplates();
});

// ─── Filter Tabs ──────────────────────────────────────────────────────────────

function setupFilterTabs(): void {
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentFilter = (tab as HTMLElement).dataset.filter ?? 'all';
            renderTemplates();
        });
    });
}

// ─── Load Templates ───────────────────────────────────────────────────────────

async function loadTemplates(): Promise<void> {
    setTableLoading(true);
    try {
        const data = await apiRequest<TemplateListResponse>(
            '/templates/admin/all',
            authService
        );
        allTemplates = data.templates ?? (data as unknown as Template[]);
        updateBadges();
        renderTemplates();
    } catch (error) {
        console.error('Failed to load templates:', error);
        setTableError(`Failed to load templates: ${(error as Error).message}`);
    }
}

function setTableLoading(isLoading: boolean): void {
    if (isLoading) {
        templatesTable.innerHTML = '<tr><td colspan="7" class="text-center">Loading…</td></tr>';
    }
}

function setTableError(message: string): void {
    templatesTable.innerHTML = `<tr><td colspan="7" class="text-center error">${message}</td></tr>`;
}

// ─── Render ───────────────────────────────────────────────────────────────────

function getApprovalStatus(t: Template): string {
    return (t.translations[0]?.approval_status ?? 'PENDING').toUpperCase();
}

function updateBadges(): void {
    const all = allTemplates.length;
    const approved = allTemplates.filter(t => getApprovalStatus(t) === 'APPROVED').length;
    const pending = allTemplates.filter(t => getApprovalStatus(t) === 'PENDING').length;
    const rejected = allTemplates.filter(t => getApprovalStatus(t) === 'REJECTED').length;

    document.getElementById('badge-all')!.textContent = String(all);
    document.getElementById('badge-approved')!.textContent = String(approved);
    document.getElementById('badge-pending')!.textContent = String(pending);
    document.getElementById('badge-rejected')!.textContent = String(rejected);
}

function renderTemplates(): void {
    const filtered = currentFilter === 'all'
        ? allTemplates
        : allTemplates.filter(t => getApprovalStatus(t) === currentFilter);

    if (filtered.length === 0) {
        templatesTable.innerHTML = '<tr><td colspan="7" class="text-center">No templates found.</td></tr>';
        return;
    }

    templatesTable.innerHTML = filtered.map(t => {
        const lang = t.translations[0]?.language?.toUpperCase() ?? '—';
        const waId = t.translations[0]?.whatsapp_template_id;
        const status = t.translations[0]?.approval_status ?? 'Not submitted';
        return `
        <tr>
            <td>
                <strong>${escapeHtml(t.template_name)}</strong>
                <br><small style="color:#6b7280;font-size:11px;">${escapeHtml(t.display_name)}</small>
                ${waId ? `<br><small style="color:#9ca3af;font-size:11px;">WA ID: ${escapeHtml(waId)}</small>` : ''}
            </td>
            <td>
                ${escapeHtml(t.campaign_type)}
                ${t.sub_segment ? `<br><small style="color:#6b7280;font-size:11px;">${escapeHtml(t.sub_segment)}</small>` : ''}
            </td>
            <td>${lang}</td>
            <td>${createStatusBadge(status)}</td>
            <td>${t.is_active
                ? '<span style="color:#10b981;font-weight:600;">✅ Yes</span>'
                : '<span style="color:#6b7280;">No</span>'}</td>
            <td>${formatDateOnly(t.created_at)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-sm btn-secondary" onclick="previewTemplate(${t.id})">👁 Preview</button>
                    <button class="btn btn-sm btn-secondary" onclick="editTemplate(${t.id})">Edit</button>
                    <button class="btn btn-sm btn-secondary" onclick="syncTemplate(${t.id})">Sync ↑</button>
                    <button class="btn btn-sm btn-secondary" onclick="checkStatus(${t.id})">Status</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteTemplate(${t.id}, '${escapeHtml(t.template_name)}')">Delete</button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

// ─── Create / Edit Modal ──────────────────────────────────────────────────────

function setupCreateModal(): void {
    const modal = document.getElementById('templateModal')!;
    const newBtn = document.getElementById('newTemplateBtn')!;

    newBtn.addEventListener('click', () => { modal.style.display = 'flex'; });
    document.getElementById('modalCloseBtn')!.addEventListener('click', closeModal);
    document.getElementById('modalCancelBtn')!.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
}

function openModal(template?: Template): void {
    const modal = document.getElementById('templateModal')!;
    const title = document.getElementById('modalTitle')!;
    const idInput = document.getElementById('templateId') as HTMLInputElement;
    const createOnlyFields = document.getElementById('createOnlyFields')!;
    const activeToggleGroup = document.getElementById('activeToggleGroup')!;
    const formError = document.getElementById('formError')!;

    formError.style.display = 'none';

    if (template) {
        // ── EDIT mode ──
        title.textContent = 'Edit Template';
        idInput.value = String(template.id);
        createOnlyFields.style.display = 'none';
        activeToggleGroup.style.display = 'block';

        (document.getElementById('displayName') as HTMLInputElement).value = template.display_name;
        (document.getElementById('templateDescription') as HTMLInputElement).value = template.description ?? '';
        (document.getElementById('isActive') as HTMLInputElement).checked = template.is_active;
    } else {
        // ── CREATE mode ──
        title.textContent = 'New Template';
        idInput.value = '';
        createOnlyFields.style.display = 'block';
        activeToggleGroup.style.display = 'none';

        (document.getElementById('templateName') as HTMLInputElement).value = '';
        (document.getElementById('campaignType') as HTMLSelectElement).value = '';
        (document.getElementById('templateCategory') as HTMLSelectElement).value = '';
        (document.getElementById('subSegment') as HTMLSelectElement).value = '';
        (document.getElementById('variableCount') as HTMLInputElement).value = '0';
        (document.getElementById('variableNames') as HTMLInputElement).value = '';
        (document.getElementById('translationLanguage') as HTMLSelectElement).value = 'en';
        (document.getElementById('headerText') as HTMLInputElement).value = '';
        (document.getElementById('bodyText') as HTMLTextAreaElement).value = '';
        (document.getElementById('footerText') as HTMLInputElement).value = '';
        (document.getElementById('displayName') as HTMLInputElement).value = '';
        (document.getElementById('templateDescription') as HTMLInputElement).value = '';
    }

    modal.style.display = 'flex';
    (document.getElementById(template ? 'displayName' : 'templateName') as HTMLElement).focus();
}

function closeModal(): void {
    document.getElementById('templateModal')!.style.display = 'none';
}

function showFormError(msg: string): void {
    const el = document.getElementById('formError')!;
    el.textContent = msg;
    el.style.display = 'block';
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function saveTemplate(): Promise<void> {
    const idInput = document.getElementById('templateId') as HTMLInputElement;
    const saveBtn = document.getElementById('modalSaveBtn') as HTMLButtonElement;
    document.getElementById('formError')!.style.display = 'none';

    const isEdit = !!idInput.value;

    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';

    try {
        if (isEdit) {
            // ── PATCH: only 3 fields allowed ──
            const displayName = (document.getElementById('displayName') as HTMLInputElement).value.trim();
            const description = (document.getElementById('templateDescription') as HTMLInputElement).value.trim();
            const isActive = (document.getElementById('isActive') as HTMLInputElement).checked;

            if (!displayName) {
                showFormError('Display name is required.');
                return;
            }

            const payload: TemplateUpdatePayload = { display_name: displayName, is_active: isActive };
            if (description) payload.description = description;

            await apiRequest(`/templates/admin/${idInput.value}`, authService, {
                method: 'PATCH',
                body: JSON.stringify(payload),
            });
            closeModal();
            showToast('Template updated.', 'success');
        } else {
            // ── POST: full TemplateCreate ──
            const templateName = (document.getElementById('templateName') as HTMLInputElement).value.trim();
            const displayName = (document.getElementById('displayName') as HTMLInputElement).value.trim();
            const campaignType = (document.getElementById('campaignType') as HTMLSelectElement).value;
            const templateCategory = (document.getElementById('templateCategory') as HTMLSelectElement).value;
            const subSegment = (document.getElementById('subSegment') as HTMLSelectElement).value;
            const description = (document.getElementById('templateDescription') as HTMLInputElement).value.trim();
            const variableCountInput = parseInt((document.getElementById('variableCount') as HTMLInputElement).value, 10);
            const variableNamesRaw = (document.getElementById('variableNames') as HTMLInputElement).value.trim();
            const language = (document.getElementById('translationLanguage') as HTMLSelectElement).value;
            const headerText = (document.getElementById('headerText') as HTMLInputElement).value.trim();
            const bodyText = (document.getElementById('bodyText') as HTMLTextAreaElement).value.trim();
            const footerText = (document.getElementById('footerText') as HTMLInputElement).value.trim();

            if (!templateName) { showFormError('Template name is required.'); return; }
            if (!displayName) { showFormError('Display name is required.'); return; }
            if (!campaignType) { showFormError('Campaign type is required.'); return; }
            if (!templateCategory) { showFormError('WhatsApp category is required.'); return; }
            if (!bodyText) { showFormError('Message body is required.'); return; }

            // Auto-count variables from body if user left count at 0
            const autoCount = (bodyText.match(/\{\{\d+\}\}/g) ?? []).length;
            const variableCount = variableCountInput > 0 ? variableCountInput : autoCount;

            const variableNames = variableNamesRaw
                ? variableNamesRaw.split(',').map(s => s.trim()).filter(Boolean)
                : undefined;

            const payload: TemplateCreatePayload = {
                template_name: templateName,
                display_name: displayName,
                campaign_type: campaignType,
                category: templateCategory,
                variable_count: variableCount,
                translations: [{
                    language,
                    body_text: bodyText,
                    ...(headerText && { header_text: headerText }),
                    ...(footerText && { footer_text: footerText }),
                }],
                ...(subSegment && { sub_segment: subSegment }),
                ...(description && { description }),
                ...(variableNames && { variable_names: variableNames }),
            };

            await apiRequest('/templates/admin/', authService, {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            closeModal();
            showToast('Template created.', 'success');
        }

        await loadTemplates();
    } catch (error) {
        showFormError((error as Error).message || 'Failed to save template. Check all required fields.');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Template';
    }
}

// ─── Sync to WhatsApp ─────────────────────────────────────────────────────────

async function syncTemplate(templateId: number): Promise<void> {
    try {
        await apiRequest(`/templates/admin/${templateId}/sync-to-whatsapp`, authService, {
            method: 'POST',
        });
        showToast('Template submitted to WhatsApp for approval.', 'success');
        await loadTemplates();
    } catch (error) {
        showToast(`Sync failed: ${(error as Error).message}`, 'error');
    }
}

function setupSyncButton(): void {
    document.getElementById('syncFromWhatsAppBtn')?.addEventListener('click', async () => {
        const btn = document.getElementById('syncFromWhatsAppBtn') as HTMLButtonElement;
        btn.disabled = true;
        btn.textContent = 'Syncing…';
        try {
            await apiRequest('/templates/admin/sync-from-whatsapp', authService, { method: 'POST' });
            showToast('Templates synced from WhatsApp.', 'success');
            await loadTemplates();
        } catch (error) {
            showToast(`Sync failed: ${(error as Error).message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = '🔄 Sync from WhatsApp';
        }
    });
}

// ─── Check Status Modal ───────────────────────────────────────────────────────

function setupStatusModal(): void {
    const modal = document.getElementById('statusModal')!;
    document.getElementById('statusModalCloseBtn')?.addEventListener('click', () => { modal.style.display = 'none'; });
    document.getElementById('statusModalDoneBtn')?.addEventListener('click', () => { modal.style.display = 'none'; });
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });
}

async function checkStatus(templateId: number): Promise<void> {
    const modal = document.getElementById('statusModal')!;
    const content = document.getElementById('statusModalContent')!;

    content.innerHTML = '<p>Loading status…</p>';
    modal.style.display = 'flex';

    try {
        const data = await apiRequest<Record<string, unknown>>(
            `/templates/admin/${templateId}/whatsapp-status`,
            authService
        );
        content.innerHTML = `<pre style="white-space:pre-wrap;font-size:13px;background:#f9fafb;padding:16px;border-radius:8px;border:1px solid #e5e7eb;">${JSON.stringify(data, null, 2)}</pre>`;
    } catch (error) {
        content.innerHTML = `<p style="color:#ef4444;">${(error as Error).message}</p>`;
    }
}

// ─── Edit Template ────────────────────────────────────────────────────────────

function editTemplate(templateId: number): void {
    const template = allTemplates.find(t => t.id === templateId);
    if (!template) {
        showToast('Template not found.', 'error');
        return;
    }
    openModal(template);
}

// ─── Delete Template ──────────────────────────────────────────────────────────

async function deleteTemplate(templateId: number, name: string): Promise<void> {
    const modal = new ConfirmationModal(
        'Delete Template',
        `Are you sure you want to delete "${name}"? This cannot be undone.`,
        'Delete',
        'Cancel'
    );

    const confirmed = await modal.show();
    if (!confirmed) return;

    try {
        await apiRequest(`/templates/admin/${templateId}`, authService, { method: 'DELETE' });
        showToast('Template deleted.', 'success');
        await loadTemplates();
    } catch (error) {
        showToast(`Delete failed: ${(error as Error).message}`, 'error');
    }
}

// ─── Utility ─────────────────────────────────────────────────────────────────

function escapeHtml(str: string): string {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

const LANG_LABELS: Record<string, string> = {
    en: 'English', hi: 'Hindi', kn: 'Kannada',
    mr: 'Marathi', ta: 'Tamil', pa: 'Punjabi',
};

function langLabel(code: string): string {
    return LANG_LABELS[code] ?? code.toUpperCase();
}

// ─── Preview Modal ────────────────────────────────────────────────────────────

function setupPreviewModal(): void {
    const modal = document.getElementById('previewModal')!;
    document.getElementById('previewModalCloseBtn')?.addEventListener('click', () => { modal.style.display = 'none'; });
    document.getElementById('previewModalDoneBtn')?.addEventListener('click', () => { modal.style.display = 'none'; });
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });
}

async function previewTemplate(templateId: number): Promise<void> {
    const modal = document.getElementById('previewModal')!;
    const title = document.getElementById('previewModalTitle')!;
    const body = document.getElementById('previewModalBody')!;

    title.textContent = 'Loading…';
    body.innerHTML = '<p>Loading preview…</p>';
    modal.style.display = 'flex';

    try {
        const data = await apiRequest<TemplatePreviewResponse>(
            `/templates/admin/${templateId}/preview`,
            authService
        );
        title.textContent = data.display_name;
        renderAdminPreview(data, body);
    } catch (error) {
        body.innerHTML = `<p style="color:#ef4444;">${escapeHtml((error as Error).message)}</p>`;
    }
}

function renderAdminPreview(data: TemplatePreviewResponse, container: HTMLElement): void {
    const translations = data.translations;
    if (translations.length === 0) {
        container.innerHTML = '<p style="color:#6b7280;">No translations available for preview.</p>';
        return;
    }

    // Language tabs
    const langTabsHtml = translations.length > 1
        ? `<div class="lang-tabs">${translations.map((t, i) =>
            `<button class="lang-tab-btn${i === 0 ? ' active' : ''}" data-idx="${i}">${langLabel(t.language)} <small>(${t.approval_status})</small></button>`
          ).join('')}</div>`
        : '';

    // Translation panels
    const panels = translations.map((t, i) => `
        <div class="tpanel" data-panel="${i}" style="${i > 0 ? 'display:none;' : ''}">
            <div class="wa-bubble">
                ${t.example_header ? `<div class="wa-bubble-header">${escapeHtml(t.example_header)}</div>` : ''}
                <div>${escapeHtml(t.example_body)}</div>
                ${t.example_footer ? `<div class="wa-bubble-footer">${escapeHtml(t.example_footer)}</div>` : ''}
            </div>
        </div>
    `).join('');

    // Variable chips
    const dummyEntries = Object.entries(data.dummy_values);
    const varsHtml = dummyEntries.length > 0
        ? `<div class="preview-vars">
             <h4>Variable Mapping (example values)</h4>
             ${dummyEntries.map(([name, val]) =>
                 `<span class="var-chip"><span class="vn">${escapeHtml(name)}</span><span class="va">→</span><span class="vv">${escapeHtml(val)}</span></span>`
             ).join('')}
           </div>`
        : '';

    // Details
    const details = `
        <div style="margin-top:16px;">
            <div class="preview-detail"><span class="lbl">Template Name</span><span class="val">${escapeHtml(data.template_name)}</span></div>
            <div class="preview-detail"><span class="lbl">Category</span><span class="val">${escapeHtml(data.category)}</span></div>
            <div class="preview-detail"><span class="lbl">Campaign Type</span><span class="val">${escapeHtml(data.campaign_type)}</span></div>
            ${data.sub_segment ? `<div class="preview-detail"><span class="lbl">Sub Segment</span><span class="val">${escapeHtml(data.sub_segment)}</span></div>` : ''}
            <div class="preview-detail"><span class="lbl">Variables</span><span class="val">${data.variable_count}</span></div>
        </div>`;

    container.innerHTML = langTabsHtml + panels + varsHtml + details;

    // Tab switching
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

// ─── Expose to HTML onclick handlers ─────────────────────────────────────────

type WindowExtras = {
    editTemplate: typeof editTemplate;
    syncTemplate: typeof syncTemplate;
    checkStatus: typeof checkStatus;
    deleteTemplate: typeof deleteTemplate;
    previewTemplate: typeof previewTemplate;
};

(window as unknown as WindowExtras).editTemplate = editTemplate;
(window as unknown as WindowExtras).syncTemplate = syncTemplate;
(window as unknown as WindowExtras).checkStatus = checkStatus;
(window as unknown as WindowExtras).deleteTemplate = deleteTemplate;
(window as unknown as WindowExtras).previewTemplate = previewTemplate;
