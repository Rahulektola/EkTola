/**
 * Jeweller Templates Page
 * Browse approved templates with preview (WhatsApp-style example messages)
 */

import { API_BASE } from '@/config/api';
import '@/services/auth';

// ─── Types ────────────────────────────────────────────────────────────────────

interface TemplateTranslation {
    id: number;
    template_id: number;
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

interface TemplateListResponse {
    templates: Template[];
    total: number;
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

// ─── State ────────────────────────────────────────────────────────────────────

let allTemplates: Template[] = [];
let currentFilter = 'all';

// ─── Auth Check ───────────────────────────────────────────────────────────────

const authService = window.authService;

if (!authService.isAuthenticated()) {
    window.location.href = '/index.html';
}

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    setupLogout();
    setupFilters();
    setupPreviewModal();
    loadTemplates();
    setupImpersonationBanner();
});

function setupImpersonationBanner(): void {
  const banner = document.getElementById('impersonation-banner');
  const exitBtn = document.getElementById('exit-impersonation');
  const jewellerNameSpan = document.getElementById('impersonation-text');
  if (!banner || !exitBtn || !jewellerNameSpan) return;
  if (authService.isImpersonating()) {
    const jeweller = authService.getImpersonatedJewellerInfo();
    if (jeweller) {
      jewellerNameSpan.textContent = `Viewing as ${jeweller.name}`;
      banner.style.display = 'flex';
    }
    exitBtn.addEventListener('click', () => {
      authService.exitImpersonation();
      window.location.href = '/admin/dashboard.html';
    });
  } else {
    banner.style.display = 'none';
  }
}

// ─── Logout ───────────────────────────────────────────────────────────────────

function setupLogout(): void {
    document.getElementById('logoutBtn')?.addEventListener('click', () => {
        authService.logout();
        window.location.href = '/index.html';
    });
}

// ─── Filters ──────────────────────────────────────────────────────────────────

function setupFilters(): void {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = (btn as HTMLElement).dataset.filter ?? 'all';
            renderTemplates();
        });
    });
}

// ─── Load Templates ───────────────────────────────────────────────────────────

async function loadTemplates(): Promise<void> {
    const grid = document.getElementById('templates-grid')!;
    grid.innerHTML = '<div class="loading-state">Loading templates…</div>';

    try {
        const headers = authService.getAuthHeaders();
        const response = await fetch(`${API_BASE}/templates/`, { headers });

        if (!response.ok) {
            throw new Error(`Failed to load templates (${response.status})`);
        }

        const data: TemplateListResponse = await response.json();
        allTemplates = data.templates ?? [];
        renderTemplates();
    } catch (error) {
        console.error('Failed to load templates:', error);
        grid.innerHTML = `
            <div class="empty-state">
                <div class="icon">⚠️</div>
                <h3>Could not load templates</h3>
                <p>${escapeHtml((error as Error).message)}</p>
            </div>`;
    }
}

// ─── Render Template Cards ────────────────────────────────────────────────────

function renderTemplates(): void {
    const grid = document.getElementById('templates-grid')!;

    const filtered = currentFilter === 'all'
        ? allTemplates
        : allTemplates.filter(t => t.campaign_type === currentFilter);

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="icon">📋</div>
                <h3>No templates found</h3>
                <p>No approved templates are available${currentFilter !== 'all' ? ` for ${currentFilter}` : ''} yet.</p>
            </div>`;
        return;
    }

    grid.innerHTML = filtered.map(t => {
        const bodyPreview = t.translations[0]?.body_text ?? 'No content';
        const langCount = t.translations.length;
        const typeClass = t.campaign_type === 'UTILITY' ? 'badge-utility' : 'badge-marketing';
        return `
        <div class="template-card" data-template-id="${t.id}">
            <div class="template-card-header">
                <h3>${escapeHtml(t.display_name)}</h3>
                <span class="badge ${typeClass}">${escapeHtml(t.campaign_type)}</span>
            </div>
            <div class="template-card-body">${escapeHtml(bodyPreview)}</div>
            <div class="template-card-meta">
                <span>📝 ${t.variable_count} variable${t.variable_count !== 1 ? 's' : ''}</span>
                <span>🌐 ${langCount} language${langCount !== 1 ? 's' : ''}</span>
                ${t.sub_segment ? `<span>🏷️ ${escapeHtml(t.sub_segment)}</span>` : ''}
            </div>
        </div>`;
    }).join('');

    // Attach click handlers
    grid.querySelectorAll('.template-card').forEach(card => {
        card.addEventListener('click', () => {
            const id = parseInt((card as HTMLElement).dataset.templateId ?? '0', 10);
            if (id) openPreview(id);
        });
    });
}

// ─── Preview Modal ────────────────────────────────────────────────────────────

function setupPreviewModal(): void {
    const modal = document.getElementById('previewModal')!;
    document.getElementById('previewCloseBtn')!.addEventListener('click', closePreview);
    modal.addEventListener('click', (e) => { if (e.target === modal) closePreview(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closePreview(); });
}

function closePreview(): void {
    document.getElementById('previewModal')!.style.display = 'none';
}

async function openPreview(templateId: number): Promise<void> {
    const modal = document.getElementById('previewModal')!;
    const title = document.getElementById('previewTitle')!;
    const body = document.getElementById('previewBody')!;

    title.textContent = 'Loading…';
    body.innerHTML = '<div class="loading-state">Loading preview…</div>';
    modal.style.display = 'flex';

    try {
        const headers = authService.getAuthHeaders();
        const response = await fetch(`${API_BASE}/templates/${templateId}/preview`, { headers });

        if (!response.ok) {
            throw new Error(`Failed to load preview (${response.status})`);
        }

        const data: TemplatePreviewResponse = await response.json();
        title.textContent = data.display_name;
        renderPreview(data, body);
    } catch (error) {
        console.error('Preview error:', error);
        body.innerHTML = `<p style="color:#ef4444;">${escapeHtml((error as Error).message)}</p>`;
    }
}

function renderPreview(data: TemplatePreviewResponse, container: HTMLElement): void {
    const translations = data.translations;
    if (translations.length === 0) {
        container.innerHTML = '<p style="color:#6b7280;">No approved translations available for preview.</p>';
        return;
    }

    // Language tabs (if multiple translations)
    const langTabsHtml = translations.length > 1
        ? `<div class="lang-tabs">${translations.map((t, i) =>
            `<button class="lang-tab${i === 0 ? ' active' : ''}" data-idx="${i}">${langLabel(t.language)}</button>`
          ).join('')}</div>`
        : '';

    // Render each translation panel
    const panels = translations.map((t, i) => `
        <div class="translation-panel" data-panel="${i}" style="${i > 0 ? 'display:none;' : ''}">
            <div class="wa-message">
                ${t.example_header ? `<div class="wa-message-header">${escapeHtml(t.example_header)}</div>` : ''}
                <div>${escapeHtml(t.example_body)}</div>
                ${t.example_footer ? `<div class="wa-message-footer">${escapeHtml(t.example_footer)}</div>` : ''}
            </div>
        </div>
    `).join('');

    // Variable mapping chips
    const dummyEntries = Object.entries(data.dummy_values);
    const variablesHtml = dummyEntries.length > 0
        ? `<div class="preview-variables">
             <h4>Variable Mapping (example values)</h4>
             ${dummyEntries.map(([name, val]) =>
                 `<span class="variable-chip">
                    <span class="var-name">${escapeHtml(name)}</span>
                    <span class="var-arrow">→</span>
                    <span class="var-value">${escapeHtml(val)}</span>
                  </span>`
             ).join('')}
           </div>`
        : '';

    // Detail rows
    const detailsHtml = `
        <div class="preview-details">
            <div class="preview-detail-row">
                <span class="label">Template Name</span>
                <span class="value">${escapeHtml(data.template_name)}</span>
            </div>
            <div class="preview-detail-row">
                <span class="label">Category</span>
                <span class="value">${escapeHtml(data.category)}</span>
            </div>
            <div class="preview-detail-row">
                <span class="label">Campaign Type</span>
                <span class="value">${escapeHtml(data.campaign_type)}</span>
            </div>
            ${data.sub_segment ? `
            <div class="preview-detail-row">
                <span class="label">Sub Segment</span>
                <span class="value">${escapeHtml(data.sub_segment)}</span>
            </div>` : ''}
            <div class="preview-detail-row">
                <span class="label">Variables</span>
                <span class="value">${data.variable_count}</span>
            </div>
        </div>`;

    container.innerHTML = langTabsHtml + panels + variablesHtml + detailsHtml;

    // Wire language tab switching
    container.querySelectorAll('.lang-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            container.querySelectorAll('.lang-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const idx = (tab as HTMLElement).dataset.idx;
            container.querySelectorAll('.translation-panel').forEach(p => {
                (p as HTMLElement).style.display = (p as HTMLElement).dataset.panel === idx ? '' : 'none';
            });
        });
    });
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

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
