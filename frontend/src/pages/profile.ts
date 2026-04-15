/**
 * Profile Page
 * Displays the authenticated jeweller's account information
 */

import { API_BASE } from '@/config/api';
import '@/services/auth';

interface JewellerProfile {
  id: number;
  business_name: string;
  owner_name: string | null;
  phone_number: string;
  email: string | null;
  approval_status: string;
  whatsapp_phone_number_id: string | null;
  created_at: string;
}

// Auth guard — redirect to login if not authenticated
if (!window.authService.isAuthenticated()) {
  window.location.href = '/index.html';
}

// Profile button → stay on page (already here)
document.getElementById('profileBtn')?.addEventListener('click', () => {
  window.location.href = '/profile.html';
});

// Logout
document.getElementById('logoutBtn')?.addEventListener('click', () => {
  window.authService.logout();
  window.location.href = '/index.html';
});

/**
 * Load and render the jeweller profile
 */
async function loadProfile(): Promise<void> {
  const loadingState = document.getElementById('loadingState')!;
  const errorState = document.getElementById('errorState')!;
  const profileContent = document.getElementById('profileContent')!;
  const errorMessage = document.getElementById('errorMessage')!;

  loadingState.style.display = 'block';
  errorState.style.display = 'none';
  profileContent.style.display = 'none';

  try {
    const response = await fetch(`${API_BASE}/auth/me/jeweller`, {
      headers: {
        ...window.authService.getAuthHeaders(),
        'Cache-Control': 'no-cache',
      },
    });

    if (response.status === 401) {
      window.authService.logout();
      window.location.href = '/index.html';
      return;
    }

    if (!response.ok) {
      throw new Error(`Failed to load profile (${response.status})`);
    }

    const profile: JewellerProfile = await response.json();
    renderProfile(profile);

    loadingState.style.display = 'none';
    profileContent.style.display = 'block';
  } catch (error) {
    console.error('Profile load error:', error);
    loadingState.style.display = 'none';
    errorMessage.textContent = (error as Error).message || 'Failed to load profile. Please try again.';
    errorState.style.display = 'block';
  }
}

/**
 * Set a text value on a DOM element safely
 */
function setText(id: string, value: string | null | undefined, fallback = '—'): void {
  const el = document.getElementById(id);
  if (el) el.textContent = value || fallback;
}

/**
 * Render profile data into the DOM
 */
function renderProfile(profile: JewellerProfile): void {
  setText('businessName', profile.business_name);
  setText('ownerName', profile.owner_name);
  setText('phoneNumber', profile.phone_number);
  setText('email', profile.email);
  setText('memberSince', formatDate(profile.created_at));
  setText('phoneNumberId', profile.whatsapp_phone_number_id);

  // Approval status pill
  const approvalEl = document.getElementById('approvalStatus');
  if (approvalEl) {
    const status = profile.approval_status?.toLowerCase() ?? '';
    const isApproved = status === 'approved';
    approvalEl.innerHTML = `
      <span class="status-pill ${isApproved ? 'approved' : 'pending'}">
        ${isApproved ? '✅' : '⏳'} ${profile.approval_status}
      </span>
    `;
  }

  // WhatsApp status pill
  const waEl = document.getElementById('whatsappStatus');
  if (waEl) {
    const connected = !!profile.whatsapp_phone_number_id;
    waEl.innerHTML = `
      <span class="status-pill ${connected ? 'connected' : 'not-connected'}">
        ${connected ? '✅ Connected' : '⚠️ Not Connected'}
      </span>
    `;
  }
}

/**
 * Format ISO date string for display
 */
function formatDate(isoString: string | null): string {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

// Make loadProfile available globally for the retry button
(window as unknown as Record<string, unknown>).loadProfile = loadProfile;

// Kick off on load
loadProfile();

// Impersonation badge
function setupImpersonationBanner(): void {
  const banner = document.getElementById('impersonation-banner');
  const exitBtn = document.getElementById('exit-impersonation');
  const jewellerNameSpan = document.getElementById('impersonation-text');
  if (!banner || !exitBtn || !jewellerNameSpan) return;
  if (window.authService.isImpersonating()) {
    const jeweller = window.authService.getImpersonatedJewellerInfo();
    if (jeweller) {
      jewellerNameSpan.textContent = `Viewing as ${jeweller.name}`;
      banner.style.display = 'flex';
    }
    exitBtn.addEventListener('click', () => {
      window.authService.exitImpersonation();
      window.location.href = '/admin/dashboard.html';
    });
  } else {
    banner.style.display = 'none';
  }
}
setupImpersonationBanner();
