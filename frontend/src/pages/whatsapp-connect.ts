/**
 * WhatsApp Embedded Signup Integration
 * Handles jeweller WhatsApp Business Account connection
 * Based on official Facebook Embedded Signup documentation
 */

import { API_BASE } from '@/config/api';

// ==================== Types ====================

interface WhatsAppSessionData {
  phone_number_id: string | null;
  waba_id: string | null;
  business_name: string | null;
}

interface WhatsAppConfig {
  appId: string;
  configId: string;
  state: string;
}

interface JewellerProfile {
  waba_id?: string;
  phone_number_id?: string;
  waba_name?: string;
  business_name?: string;
  phone_display_number?: string;
  business_verification_status?: string;
}

interface WhatsAppCallbackResult {
  success: boolean;
  business_name?: string;
  phone_display_number?: string;
  error?: string;
  detail?: string;
}

// ==================== State Management ====================

let whatsappSessionData: WhatsAppSessionData = {
  phone_number_id: null,
  waba_id: null,
  business_name: null
};

// Store config data from backend
window.__whatsappConfigData = null;

// ==================== Utility Functions ====================

function getAuthToken(): string | null {
  return localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
}

function showLoading(message: string): void {
  const loader = document.getElementById('whatsapp-loading');
  if (loader) {
    loader.style.display = 'flex';
    const msgEl = loader.querySelector('.loading-message');
    if (msgEl) msgEl.textContent = message || 'Processing...';
  }
  console.log('[WhatsApp] Loading:', message);
}

function hideLoading(): void {
  const loader = document.getElementById('whatsapp-loading');
  if (loader) {
    loader.style.display = 'none';
  }
}

function showSuccess(message: string): void {
  // Use your app's notification system
  console.log('[WhatsApp] ✓ Success:', message);
  alert('✓ ' + message);
}

function showError(message: string): void {
  console.error('[WhatsApp] ✗ Error:', message);
  alert('✗ Error: ' + message);
}

function showWarning(message: string): void {
  console.warn('[WhatsApp] ⚠ Warning:', message);
}

// ==================== Facebook MessageEvent Listener ====================
// This captures session info (phone_number_id, waba_id) directly from the popup

window.addEventListener('message', (event: MessageEvent) => {
  // Security: Only accept messages from Facebook
  if (event.origin !== "https://www.facebook.com" && 
      event.origin !== "https://web.facebook.com") {
    return;
  }

  try {
    const data = JSON.parse(event.data as string);
    
    // Check if it's WhatsApp Embedded Signup event
    if (data.type === 'WA_EMBEDDED_SIGNUP') {
      console.log('[WhatsApp] Received event:', data.event);
      
      // User completed the signup flow
      if (data.event === 'FINISH') {
        const { phone_number_id, waba_id } = data.data;
        console.log('[WhatsApp] ✓ Signup Completed');
        console.log('[WhatsApp]   Phone Number ID:', phone_number_id);
        console.log('[WhatsApp]   WABA ID:', waba_id);
        
        // Store in state for backend call
        whatsappSessionData.phone_number_id = phone_number_id;
        whatsappSessionData.waba_id = waba_id;
      } 
      
      // User cancelled the flow
      else if (data.event === 'CANCEL') {
        const { current_step } = data.data;
        console.warn('[WhatsApp] ✗ User cancelled at step:', current_step);
        showWarning('WhatsApp signup was cancelled at step: ' + current_step);
        hideLoading();
      } 
      
      // Error occurred during flow
      else if (data.event === 'ERROR') {
        const { error_message } = data.data;
        console.error('[WhatsApp] ✗ Signup error:', error_message);
        showError('WhatsApp signup error: ' + error_message);
        hideLoading();
      }
      
      // Log full event data for debugging
      console.log('[WhatsApp] Full session data:', JSON.stringify(data, null, 2));
      
      // Update debug display if exists
      const debugEl = document.getElementById('session-info-response');
      if (debugEl) {
        debugEl.textContent = JSON.stringify(data, null, 2);
      }
    }
  } catch {
    // Non-JSON responses (ignore)
    console.log('[WhatsApp] Non-JSON message:', event.data);
  }
});

// ==================== FB.login Callback ====================

interface FBAuthResponse {
  authResponse?: {
    code?: string;
  };
}

const fbLoginCallback = (response: FBAuthResponse): void => {
  console.log('[WhatsApp] Facebook login response:', response);
  
  // Update debug display if exists
  const debugEl = document.getElementById('sdk-response');
  if (debugEl) {
    debugEl.textContent = JSON.stringify(response, null, 2);
  }
  
  if (response.authResponse) {
    const code = response.authResponse.code;
    console.log('[WhatsApp] ✓ Authorization code received');
    
    // Get state token from backend config call
    if (!window.__whatsappConfigData || !window.__whatsappConfigData.state) {
      showError('Configuration error. Please refresh and try again.');
      hideLoading();
      return;
    }
    
    // Send code to backend (async handled internally)
    if (code) {
      handleWhatsAppCallback(code, window.__whatsappConfigData.state);
    }
  } else {
    console.warn('[WhatsApp] ✗ No auth response from Facebook');
    showError('Facebook login failed or was cancelled. Please try again.');
    hideLoading();
  }
};

// ==================== Handle Backend Callback ====================

async function handleWhatsAppCallback(code: string, state: string): Promise<void> {
  try {
    showLoading('Connecting WhatsApp Business Account...');
    
    console.log('[WhatsApp] Sending callback to backend...');
    console.log('[WhatsApp]   Session Data:', whatsappSessionData);
    
    const response = await fetch(`${API_BASE}/auth/whatsapp/callback`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getAuthToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        code: code, 
        state: state
      })
    });

    const result: WhatsAppCallbackResult = await response.json();
    
    if (response.ok && result.success) {
      console.log('[WhatsApp] ✓ Connected successfully:', result);
      
      showSuccess(
        `WhatsApp Connected!\n` +
        `Business: ${result.business_name || 'N/A'}\n` +
        `Phone: ${result.phone_display_number || 'N/A'}`
      );
      
      // Update UI to show connected state
      updateWhatsAppUI(true, result);
      
      // Reload page to reflect changes
      setTimeout(() => {
        window.location.reload();
      }, 2000);
      
    } else {
      console.error('[WhatsApp] ✗ Backend callback failed:', result);
      showError(result.error || result.detail || 'Failed to connect WhatsApp');
    }
    
  } catch (error) {
    console.error('[WhatsApp] ✗ Callback error:', error);
    showError('Failed to complete WhatsApp connection. Please try again.');
  } finally {
    hideLoading();
  }
}

// ==================== Launch WhatsApp Signup ====================

async function launchWhatsAppSignup(): Promise<void> {
  try {
    showLoading('Preparing WhatsApp signup...');
    
    // Reset session data
    whatsappSessionData = {
      phone_number_id: null,
      waba_id: null,
      business_name: null
    };
    
    // Get configuration from backend
    console.log('[WhatsApp] Fetching backend configuration...');
    const response = await fetch(`${API_BASE}/auth/whatsapp/config`, {
      headers: {
        'Authorization': `Bearer ${getAuthToken()}`
      }
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get WhatsApp configuration');
    }

    const config: WhatsAppConfig = await response.json();
    console.log('[WhatsApp] ✓ Backend config received:', config);
    
    // Store config for callback use
    window.__whatsappConfigData = config;
    
    hideLoading();
    
    // Check if Facebook SDK is loaded
    if (typeof FB === 'undefined') {
      showError('Facebook SDK not loaded. Please wait a moment and try again.');
      return;
    }
    
    console.log('[WhatsApp] Launching Facebook Embedded Signup...');
    console.log('[WhatsApp]   App ID:', config.appId);
    console.log('[WhatsApp]   Config ID:', config.configId);
    
    // Launch Facebook Embedded Signup
    FB.login(fbLoginCallback, {
      config_id: config.configId,           // Your configuration ID from backend
      response_type: 'code',                // Must be 'code' for System User token
      override_default_response_type: true,
      extras: {
        setup: {},
        featureType: 'whatsapp_embedded_signup',
        sessionInfoVersion: 2 // Enable session info via postMessage
      }
    });
    
  } catch (error) {
    console.error('[WhatsApp] ✗ Launch error:', error);
    showError((error as Error).message || 'Failed to launch WhatsApp signup');
    hideLoading();
  }
}

// ==================== Check WhatsApp Status ====================

async function checkWhatsAppStatus(): Promise<void> {
  try {
    console.log('[WhatsApp] Checking connection status...');
    
    const token = getAuthToken();
    if (!token) {
      console.log('[WhatsApp] No auth token, skipping status check');
      return;
    }
    
    const response = await fetch(`${API_BASE}/auth/me/jeweller`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      console.error('[WhatsApp] Failed to fetch jeweller profile');
      return;
    }

    const jeweller: JewellerProfile = await response.json();
    console.log('[WhatsApp] Jeweller profile:', jeweller);
    
    const isConnected = !!(jeweller.waba_id && jeweller.phone_number_id);
    updateWhatsAppUI(isConnected, jeweller);
    
  } catch (error) {
    console.error('[WhatsApp] Error checking status:', error);
  }
}

// ==================== Update UI ====================

function updateWhatsAppUI(isConnected: boolean, data: JewellerProfile | WhatsAppCallbackResult = {}): void {
  const notConnectedDiv = document.getElementById('whatsapp-not-connected');
  const connectedDiv = document.getElementById('whatsapp-connected');
  
  if (!notConnectedDiv || !connectedDiv) {
    console.warn('[WhatsApp] UI elements not found on page');
    return;
  }
  
  if (isConnected) {
    console.log('[WhatsApp] ✓ WhatsApp is connected');
    notConnectedDiv.style.display = 'none';
    connectedDiv.style.display = 'block';
    
    // Update connection details
    const wabaNameEl = document.getElementById('waba-name');
    const phoneDisplayEl = document.getElementById('phone-display');
    const verificationStatusEl = document.getElementById('verification-status');
    
    const profile = data as JewellerProfile;
    if (wabaNameEl) wabaNameEl.textContent = profile.waba_name || profile.business_name || 'N/A';
    if (phoneDisplayEl) phoneDisplayEl.textContent = profile.phone_display_number || 'N/A';
    if (verificationStatusEl) {
      const status = profile.business_verification_status || 'pending';
      verificationStatusEl.textContent = status;
      verificationStatusEl.className = `badge ${status === 'verified' ? 'badge-success' : 'badge-warning'}`;
    }
    
  } else {
    console.log('[WhatsApp] WhatsApp is not connected');
    notConnectedDiv.style.display = 'block';
    connectedDiv.style.display = 'none';
  }
}

// ==================== Disconnect WhatsApp ====================

async function disconnectWhatsApp(): Promise<void> {
  if (!confirm('Are you sure you want to disconnect your WhatsApp Business Account?\n\nYou will no longer be able to send campaigns until you reconnect.')) {
    return;
  }

  try {
    showLoading('Disconnecting WhatsApp...');
    
    const response = await fetch(`${API_BASE}/auth/whatsapp/disconnect`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${getAuthToken()}`
      }
    });

    const result = await response.json();
    
    if (response.ok && result.success) {
      showSuccess('WhatsApp disconnected successfully');
      
      // Update UI
      updateWhatsAppUI(false);
      
      // Reload page
      setTimeout(() => {
        window.location.reload();
      }, 1500);
      
    } else {
      showError(result.detail || 'Failed to disconnect WhatsApp');
    }
    
  } catch (error) {
    console.error('[WhatsApp] Disconnect error:', error);
    showError('Failed to disconnect WhatsApp. Please try again.');
  } finally {
    hideLoading();
  }
}

// ==================== Initialize ====================

// Check status when page loads
document.addEventListener('DOMContentLoaded', () => {
  console.log('[WhatsApp] Connect module loaded');
  
  // Only check status if we're on a page with WhatsApp UI elements
  if (document.getElementById('whatsapp-not-connected') || 
      document.getElementById('whatsapp-connected')) {
    checkWhatsAppStatus();
  }
});

// Make functions globally available
window.launchWhatsAppSignup = launchWhatsAppSignup;
window.disconnectWhatsApp = disconnectWhatsApp;
window.checkWhatsAppStatus = checkWhatsAppStatus;

console.log('[WhatsApp] whatsapp-connect.ts loaded');
