
//updated the server for demo purposes

import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  publicDir: 'public',
  
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },

  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        // Main pages
        main: resolve(__dirname, 'index.html'),
        register: resolve(__dirname, 'register.html'),
        dashboard: resolve(__dirname, 'dashboard.html'),
        contacts: resolve(__dirname, 'contacts.html'),
        offline: resolve(__dirname, 'offline.html'),
        
        // Admin pages
        adminLogin: resolve(__dirname, 'admin-login.html'),
        adminRegister: resolve(__dirname, 'admin-register.html'),
        adminDashboard: resolve(__dirname, 'admin/dashboard.html'),
        adminJewellers: resolve(__dirname, 'admin/jewellers.html'),
        adminJewellerDetail: resolve(__dirname, 'admin/jeweller-detail.html'),
        adminAnalytics: resolve(__dirname, 'admin/analytics.html'),
        adminDeletedContacts: resolve(__dirname, 'admin/deleted-contacts.html'),
        adminTemplates: resolve(__dirname, 'admin/templates.html'),
        profile: resolve(__dirname, 'profile.html'),
      },
    },
  },

  // host and allowerdHosts added.
 server: {
  host: '0.0.0.0',
  port: 3000,
  open: true,
  allowedHosts: true,
  hmr: {
    host: 'localhost',
    port: 3000,
  },
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
},

  plugins: [
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'robots.txt', 'apple-touch-icon.png'],
      manifest: {
        name: 'ekTola Jeweller WhatsApp',
        short_name: 'ekTola',
        description: 'WhatsApp Business messaging for jewellers',
        theme_color: '#6366f1',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\./i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 10,
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60, // 1 hour
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
        ],
      },
    }),
  ],
});
