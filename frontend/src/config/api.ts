/**
 * API Configuration
 * Centralized API base URL using Vite environment variables
 */

/**
 * Base URL for all API requests
 * Uses VITE_API_URL from environment variables
 * Defaults to /api proxy path if not set
 */
export const API_BASE: string = import.meta.env.VITE_API_URL || '/api';

/**
 * Build full API URL from endpoint path
 * @param endpoint - API endpoint path (e.g., '/auth/login')
 * @returns Full API URL
 */
export function apiUrl(endpoint: string): string {
  // Ensure endpoint starts with /
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE}${path}`;
}

/**
 * Environment helper
 */
export const isDevelopment = import.meta.env.DEV;
export const isProduction = import.meta.env.PROD;
