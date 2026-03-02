/**
 * Global Type Declarations
 * Types for third-party libraries and window extensions
 */

// Vite environment variables
interface ImportMetaEnv {
  readonly VITE_API_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Facebook SDK types
interface FBLoginResponse {
  status: 'connected' | 'not_authorized' | 'unknown';
  authResponse?: {
    accessToken: string;
    expiresIn: number;
    signedRequest: string;
    userID: string;
    code?: string;
  };
}

interface FBLoginOptions {
  config_id?: string;
  response_type?: string;
  override_default_response_type?: boolean;
  scope?: string;
  extras?: {
    setup?: Record<string, unknown>;
    featureType?: string;
    sessionInfoVersion?: number;
  };
}

interface FB {
  login(callback: (response: FBLoginResponse) => void, options?: FBLoginOptions): void;
  logout(callback?: (response: FBLoginResponse) => void): void;
  getLoginStatus(callback: (response: FBLoginResponse) => void): void;
  init(params: {
    appId: string;
    cookie?: boolean;
    xfbml?: boolean;
    version: string;
  }): void;
}

// Window extensions for global functions and services
declare global {
  // Facebook SDK global
  const FB: FB | undefined;
  
  interface Window {
    // Facebook SDK
    FB: FB;
    fbAsyncInit: () => void;
    
    // WhatsApp config
    __whatsappConfigData: {
      appId: string;
      configId: string;
      state: string;
    } | null;
    
    // WhatsApp connect functions
    launchWhatsAppSignup: () => Promise<void>;
    disconnectWhatsApp: () => Promise<void>;
    checkWhatsAppStatus: () => Promise<void>;
    
    // AuthService (for legacy compatibility)
    AuthService: typeof import('../services/auth').AuthService;
    authService: import('../services/auth').AuthService;
    
    // Dashboard functions
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
    
    // Admin functions
    viewJeweller: (id: number) => void;
    impersonateJeweller: (id: number, businessName: string) => Promise<void>;
    approveJeweller: (id: number) => Promise<void>;
    deleteJeweller: (id: number, businessName: string) => Promise<void>;
  }
}

export {};
