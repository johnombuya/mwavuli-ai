/**
 * API Client for Mwavuli Backend
 * 
 * Uses Next.js rewrites to proxy requests to backend
 * All requests go through /api which is rewritten to backend
 */

import axios, { AxiosInstance } from 'axios';
import type {
  SummaryStats,
  RiskDistribution,
  CountyAnalysis,
  KeywordTrend,
  ToxicityTrend,
  HourlyPattern,
  DailyPattern,
  DetectionComparison,
  GeographicHeatmap,
  RecentReportsResponse,
  DetectionRiskMatrixResponse,
  ConfidenceHistogramResponse,
  UrlMentionRiskResponse,
  TopTokensResponse,
  StatusSummaryResponse,
  ApiHealth,
} from '@/types/api';

// Create axios instance with base URL
// Uses Next.js rewrite, so /api is proxied to backend
const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle errors consistently
    if (error.response) {
      // Server responded with error
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      // Request made but no response
      console.error('Network Error:', error.request);
    } else {
      // Something else happened
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export type BaseFilterParams = {
  start_date?: string;
  end_date?: string;
  sector?: string;
  org_id?: string;
};

export type TopicCluster = {
  id: string;
  computed_at: string;
  cluster_label: number;
  size: number;
  representative_text?: string;
  top_keywords: string[];
  county_distribution: Record<string, number>;
  risk_breakdown: Record<string, number>;
  first_seen?: string;
  last_seen?: string;
  is_active: boolean;
};

export type LexiconSuggestion = {
  keyword: string;
  frequency: number;
  cluster_count: number;
  total_reports: number;
  high_reports: number;
  top_counties: { county: string; count: number }[];
};

// Analytics API endpoints
export const analyticsApi = {
  getSummary: async (params?: BaseFilterParams): Promise<SummaryStats> => {
    const response = await api.get('/v1/analytics/summary', { params });
    return response.data;
  },

  getRiskDistribution: async (params?: BaseFilterParams): Promise<RiskDistribution> => {
    const response = await api.get('/v1/analytics/risk-distribution', { params });
    return response.data;
  },

  getCountyAnalysis: async (params?: BaseFilterParams & { county?: string }): Promise<CountyAnalysis> => {
    const response = await api.get('/v1/analytics/county-analysis', { params });
    return response.data;
  },

  getKeywordTrends: async (params?: BaseFilterParams & { limit?: number }): Promise<{ keywords: KeywordTrend[]; total_keywords: number }> => {
    const response = await api.get('/v1/analytics/keyword-trends', { params });
    return response.data;
  },

  getToxicityTrends: async (params?: BaseFilterParams & { days?: number }): Promise<{ trends: ToxicityTrend[]; period_days: number }> => {
    const response = await api.get('/v1/analytics/toxicity-trends', { params });
    return response.data;
  },

  getHourlyPatterns: async (params?: BaseFilterParams): Promise<{ patterns: HourlyPattern; pattern_type: string }> => {
    const response = await api.get('/v1/analytics/hourly-patterns', { params });
    return response.data;
  },

  /**
   * Get daily patterns (day of week)
   */
  getDailyPatterns: async (params?: BaseFilterParams): Promise<{ patterns: DailyPattern; pattern_type: string }> => {
    const response = await api.get('/v1/analytics/daily-patterns', { params });
    return response.data;
  },

  getDetectionComparison: async (params?: BaseFilterParams): Promise<DetectionComparison> => {
    const response = await api.get('/v1/analytics/detection-comparison', { params });
    return response.data;
  },

  getGeographicHeatmap: async (params?: BaseFilterParams): Promise<GeographicHeatmap> => {
    const response = await api.get('/v1/analytics/geographic-heatmap', { params });
    return response.data;
  },

  getRecentReports: async (params?: { limit?: number; status?: string }): Promise<RecentReportsResponse> => {
    const response = await api.get('/v1/analytics/recent', { params });
    return response.data;
  },

  getTopTokens: async (params?: BaseFilterParams & { limit?: number; risk_levels?: string }): Promise<TopTokensResponse> => {
    const response = await api.get('/v1/analytics/top-tokens', { params });
    return response.data;
  },

  getDetectionRiskMatrix: async (params?: BaseFilterParams): Promise<DetectionRiskMatrixResponse> => {
    const response = await api.get('/v1/analytics/detection-risk-matrix', { params });
    return response.data;
  },

  getConfidenceHistogram: async (params?: BaseFilterParams & { bucket_size?: number }): Promise<ConfidenceHistogramResponse> => {
    const response = await api.get('/v1/analytics/confidence-histogram', { params });
    return response.data;
  },

  getUrlMentionRisk: async (params?: BaseFilterParams): Promise<UrlMentionRiskResponse> => {
    const response = await api.get('/v1/analytics/url-mention-risk', { params });
    return response.data;
  },

  getStatusSummary: async (params?: BaseFilterParams): Promise<StatusSummaryResponse> => {
    const response = await api.get('/v1/analytics/status-summary', { params });
    return response.data;
  },

  /**
   * Check API health
   */
  getHealth: async (): Promise<ApiHealth> => {
    const response = await api.get('/v1/health');
    return response.data;
  },

  getNationalRiskLevel: async (): Promise<{ level: string; high_pct: number; medium_pct: number; total_reports: number }> => {
    const response = await api.get('/v1/analytics/national-risk-level');
    return response.data;
  },

  getDailySummary: async (): Promise<{ summary: string; stats: SummaryStats }> => {
    const response = await api.get('/v1/analytics/daily-summary');
    return response.data;
  },

  getTopicClusters: async (): Promise<{ clusters: TopicCluster[]; count: number }> => {
    const response = await api.get('/v1/analytics/topic-clusters');
    return response.data;
  },

  getLexiconSuggestions: async (params?: { min_high_pct?: number; top_n?: number }): Promise<{ suggestions: LexiconSuggestion[]; count: number }> => {
    const response = await api.get('/v1/analytics/lexicon-suggestions', { params });
    return response.data;
  },

  getExecutiveSummary: async (): Promise<{ summary: string; generated_at: string; data: Record<string, unknown> }> => {
    const response = await api.get('/v1/analytics/executive-summary');
    return response.data;
  },
};

// Admin API
export const adminApi = {
  getEmergencyMode: async (): Promise<{ emergency_mode: boolean }> => {
    const response = await api.get('/v1/admin/emergency-mode');
    return response.data;
  },
};

// Reports API
export const reportsApi = {
  updateStatus: async (reportId: string, status: string) => {
    const response = await api.patch(`/v1/reports/${reportId}`, { status });
    return response.data;
  },

  getAppeals: async (params?: { status?: string; limit?: number }) => {
    const response = await api.get('/v1/reports/appeals', { params });
    return response.data;
  },

  resolveAppeal: async (appealId: string, body: { resolution: string; notes?: string }) => {
    const response = await api.post(`/v1/reports/appeals/${appealId}/resolve`, body);
    return response.data;
  },
};

// Verification API endpoints
export const verificationApi = {
  verifyText: async (data: { text: string; sender_id: string; county?: string }) => {
    const response = await api.post('/v1/verify/text', data);
    return response.data;
  },

  verifyMedia: async (data: { media_url: string; media_type: string; sender_id: string; county?: string }) => {
    const response = await api.post('/v1/verify/media', data);
    return response.data;
  },
};

// Backward-compat alias used by verify page
export const verifyApi = verificationApi;
export type VerifyResponse = {
  risk_level: string;
  messages: { english: string; swahili: string; sheng: string };
  report_id?: string;
  prebunking_tip: string;
  scores?: Record<string, number>;
  matched_keyword?: string;
  explanation?: string;
};

export default api;
