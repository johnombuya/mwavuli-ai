// TypeScript types for API responses

export interface SummaryStats {
  total_reports: number;
  risk_distribution: {
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    UNKNOWN: number;
  };
  avg_toxicity: number;
  top_keywords: Array<{ keyword: string; count: number }>;
  top_counties: Array<{ county: string; count: number }>;
  date_range: {
    start: string | null;
    end: string | null;
  };
}

export interface RiskDistribution {
  distribution: {
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    UNKNOWN: number;
  };
  total: number;
}

export interface CountyAnalysis {
  counties: Record<string, {
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    total: number;
    high_percentage: number;
    medium_percentage: number;
    low_percentage: number;
  }>;
}

export interface KeywordTrend {
  keyword: string;
  count: number;
}

export interface ToxicityTrend {
  date: string;
  avg_toxicity: number;
  count: number;
}

export interface HourlyPattern {
  [hour: string]: {
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    total: number;
    high_percentage: number;
    medium_percentage: number;
    low_percentage: number;
  };
}

export interface DailyPattern {
  [day: string]: {
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    total: number;
    high_percentage: number;
    medium_percentage: number;
    low_percentage: number;
  };
}

export interface DetectionComparison {
  comparison: {
    lexicon_detected: number;
    gemini_detected: number;
    both_detected: number;
    neither_detected: number;
    total: number;
    lexicon_percentage: number;
    gemini_percentage: number;
    both_percentage: number;
    neither_percentage: number;
  };
}

export interface GeographicHeatmap {
  counties: Record<string, {
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    total: number;
    avg_toxicity: number;
    risk_score: number;
    high_percentage: number;
  }>;
}

export interface ApiHealth {
  status: string;
  timestamp: string;
  services: {
    database: string;
    analyzer: string;
  };
}
