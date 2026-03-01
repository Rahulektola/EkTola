/**
 * Admin Analytics Dashboard
 * System-wide analytics and visualizations
 */

import '@/services/auth';  // Initialize global authService
import {
    checkAdminAuth,
    AdminNavigation,
    formatNumber,
    formatPercentage,
    apiRequest
} from '@/admin/common';
import type { AuthService } from '@/services/auth';

const authService = window.authService as AuthService;

interface LanguageDistribution {
    language: string;
    message_count: number;
    percentage: number;
}

interface CampaignTypeDistribution {
    campaign_type: string;
    count: number;
    percentage: number;
}

interface FailureBreakdown {
    failure_reason: string;
    count: number;
}

interface DailyVolume {
    date: string;
    count: number;
}

interface AnalyticsData {
    total_messages: number;
    language_distribution: LanguageDistribution[];
    campaign_type_distribution: CampaignTypeDistribution[];
    failure_breakdown: FailureBreakdown[];
    daily_message_volume: DailyVolume[];
}

let currentDays = 30;

document.addEventListener('DOMContentLoaded', () => {
    if (!checkAdminAuth(authService)) {
        return;
    }

    new AdminNavigation('admin-nav-container', 'analytics');

    setupEventListeners();
    loadAnalytics();
});

/**
 * Setup event listeners
 */
function setupEventListeners(): void {
    const daysSelect = document.getElementById('days-select') as HTMLSelectElement;
    daysSelect.addEventListener('change', () => {
        currentDays = parseInt(daysSelect.value);
        loadAnalytics();
    });
}

/**
 * Load analytics data
 */
async function loadAnalytics(): Promise<void> {
    const loadingState = document.getElementById('loading-state')!;
    const analyticsContent = document.getElementById('analytics-content')!;

    loadingState.style.display = 'flex';
    analyticsContent.style.display = 'none';

    try {
        const data = await apiRequest<AnalyticsData>(
            `/analytics/admin/detailed?days=${currentDays}`,
            authService
        );

        renderAnalytics(data);
        
        loadingState.style.display = 'none';
        analyticsContent.style.display = 'block';
    } catch (error) {
        console.error('Failed to load analytics:', error);
        loadingState.style.display = 'none';
        alert('Failed to load analytics: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
}

/**
 * Render analytics charts
 */
function renderAnalytics(data: AnalyticsData): void {
    // Total messages
    document.getElementById('total-messages')!.textContent = formatNumber(data.total_messages);

    // Language distribution
    renderLanguageChart(data.language_distribution);

    // Campaign type distribution
    renderCampaignTypeChart(data.campaign_type_distribution);

    // Failure breakdown
    renderFailureChart(data.failure_breakdown);

    // Daily volume
    renderDailyVolumeChart(data.daily_message_volume);
}

/**
 * Render language distribution as table
 */
function renderLanguageChart(languages: LanguageDistribution[]): void {
    const container = document.getElementById('language-chart')!;
    
    if (languages.length === 0) {
        container.innerHTML = '<p>No data available</p>';
        return;
    }

    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Language</th>
                    <th>Messages</th>
                    <th>Percentage</th>
                </tr>
            </thead>
            <tbody>
                ${languages.map(lang => `
                    <tr>
                        <td>${lang.language}</td>
                        <td>${formatNumber(lang.message_count)}</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${lang.percentage}%"></div>
                                <span class="progress-text">${formatPercentage(lang.percentage)}</span>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

/**
 * Render campaign type distribution
 */
function renderCampaignTypeChart(types: CampaignTypeDistribution[]): void {
    const container = document.getElementById('campaign-type-chart')!;
    
    if (types.length === 0) {
        container.innerHTML = '<p>No data available</p>';
        return;
    }

    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Campaign Type</th>
                    <th>Count</th>
                    <th>Percentage</th>
                </tr>
            </thead>
            <tbody>
                ${types.map(type => `
                    <tr>
                        <td>${type.campaign_type}</td>
                        <td>${formatNumber(type.count)}</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${type.percentage}%"></div>
                                <span class="progress-text">${formatPercentage(type.percentage)}</span>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

/**
 * Render failure breakdown
 */
function renderFailureChart(failures: FailureBreakdown[]): void {
    const container = document.getElementById('failure-chart')!;
    
    if (failures.length === 0) {
        container.innerHTML = '<p>No failures in this period</p>';
        return;
    }

    const maxCount = Math.max(...failures.map(f => f.count));

    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Failure Reason</th>
                    <th>Count</th>
                    <th>Distribution</th>
                </tr>
            </thead>
            <tbody>
                ${failures.map(failure => `
                    <tr>
                        <td>${failure.failure_reason || 'Unknown'}</td>
                        <td>${formatNumber(failure.count)}</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill progress-error" style="width: ${(failure.count / maxCount) * 100}%"></div>
                                <span class="progress-text">${formatNumber(failure.count)}</span>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

/**
 * Render daily volume chart
 */
function renderDailyVolumeChart(dailyData: DailyVolume[]): void {
    const container = document.getElementById('daily-volume-chart')!;
    
    if (dailyData.length === 0) {
        container.innerHTML = '<p>No data available</p>';
        return;
    }

    const maxCount = Math.max(...dailyData.map(d => d.count));

    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Messages</th>
                    <th>Volume</th>
                </tr>
            </thead>
            <tbody>
                ${dailyData.map(day => `
                    <tr>
                        <td>${day.date}</td>
                        <td>${formatNumber(day.count)}</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill progress-info" style="width: ${(day.count / maxCount) * 100}%"></div>
                                <span class="progress-text">${formatNumber(day.count)}</span>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}
