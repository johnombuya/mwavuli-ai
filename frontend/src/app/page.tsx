'use client';

import { useLanguage } from '@/contexts/LanguageContext';
import { SummaryCards } from '@/components/dashboard/SummaryCards';
import { RiskDistributionChart } from '@/components/charts/RiskDistributionChart';
import { KeywordTrendsChart } from '@/components/charts/KeywordTrendsChart';
import { TopTokensChart } from '@/components/charts/TopTokensChart';
import { ToxicityTrendsChart } from '@/components/charts/ToxicityTrendsChart';
import { HourlyPatternsChart } from '@/components/charts/HourlyPatternsChart';
import { CountyHeatmap } from '@/components/dashboard/CountyHeatmap';
import { RecentReports } from '@/components/dashboard/RecentReports';
import { DateRangePicker } from '@/components/ui/DateRangePicker';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DetectionRiskChart } from '@/components/charts/DetectionRiskChart';
import { ConfidenceHistogramChart } from '@/components/charts/ConfidenceHistogramChart';
import { UrlMentionRiskChart } from '@/components/charts/UrlMentionRiskChart';
import { NationalRiskIndicator } from '@/components/dashboard/NationalRiskIndicator';
import { DailySummaryCard } from '@/components/dashboard/DailySummaryCard';
import { CoordinatedCampaignsWidget } from '@/components/dashboard/CoordinatedCampaignsWidget';
import { TopicClustersWidget } from '@/components/dashboard/TopicClustersWidget';
import { LexiconSuggestionsWidget } from '@/components/dashboard/LexiconSuggestionsWidget';
import { adminApi } from '@/lib/api';

const chartCardClass =
  'bg-white rounded-xl border border-slate-200/60 shadow-sm p-6';
const chartTitleClass = 'text-xl font-semibold text-slate-900 mb-1';
const chartDescClass = 'text-sm text-slate-500 mb-3';

export default function DashboardPage() {
  const { t } = useLanguage();
  const [dateRange, setDateRange] = useState<{
    start_date?: string;
    end_date?: string;
    sector?: string;
    org_id?: string;
  }>({});

  const { data: emData } = useQuery({
    queryKey: ['admin', 'emergency-mode'],
    queryFn: () => adminApi.getEmergencyMode(),
    refetchInterval: 30_000,
  });
  const isEmergency = emData?.emergency_mode === true;

  return (
    <div className="p-6 md:p-8">
      <div className="max-w-7xl mx-auto">
        {isEmergency && (
          <div className="mb-4 rounded-xl bg-red-600 text-white px-5 py-3 font-semibold text-center shadow-lg animate-pulse">
            EMERGENCY MODE ACTIVE &mdash; Dashboards refreshing every 30 s, alert thresholds lowered.
          </div>
        )}

        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">
            {t.dashboardTitle}
          </h1>
          <p className="text-slate-600">
            {t.dashboardSubtitle}
          </p>
        </div>

        {/* Date Range Picker, Sector filter, and Export */}
        <div className="mb-6 flex flex-wrap items-center gap-4">
          <DateRangePicker
            onDateChange={(dr) => setDateRange((prev) => ({ ...prev, ...dr }))}
            startDate={dateRange.start_date}
            endDate={dateRange.end_date}
          />
          <select
            value={dateRange.sector || ''}
            onChange={(e) => setDateRange((prev) => ({ ...prev, sector: e.target.value || undefined }))}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700"
          >
            <option value="">All sectors</option>
            <option value="political">Political</option>
            <option value="health">Health</option>
            <option value="security">Security</option>
            <option value="fraud">Fraud</option>
          </select>
          <a
            href={`/api/v1/export/report-pack${dateRange.start_date || dateRange.end_date ? '?' + new URLSearchParams({
              ...(dateRange.start_date && { start_date: dateRange.start_date }),
              ...(dateRange.end_date && { end_date: dateRange.end_date }),
            }).toString() : ''}`}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            download
          >
            Export report pack
          </a>
        </div>

        {/* National Risk Indicator + Daily Summary */}
        <div className="mb-6 space-y-4">
          <NationalRiskIndicator />
          <DailySummaryCard />
        </div>

        {/* Summary Cards */}
        <div className="mb-8">
          <p className="text-sm text-slate-500 mb-3">Cumulative report counts across all time, broken down by risk category.</p>
          <SummaryCards dateRange={dateRange} />
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>{t.riskDistribution}</h2>
            <p className={chartDescClass}>Proportion of reports classified as HIGH, MEDIUM, or LOW risk.</p>
            <RiskDistributionChart dateRange={dateRange} />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>{t.topKeywords}</h2>
            <p className={chartDescClass}>How flagged keyword volumes change over time &mdash; useful for spotting emerging narratives.</p>
            <KeywordTrendsChart dateRange={dateRange} />
            <div className="mt-4 border-t pt-4 text-sm text-slate-600">
              <p className="font-medium mb-1">Top tokens in high-risk reports</p>
              <p className={chartDescClass}>Most frequent tokens found in high-risk reports.</p>
              <TopTokensChart dateRange={dateRange} />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 mb-8">
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>{t.toxicityTrends}</h2>
            <p className={chartDescClass}>Average toxicity scores over time, tracking changes in content severity.</p>
            <ToxicityTrendsChart dateRange={dateRange} />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>{t.hourlyPatterns}</h2>
            <p className={chartDescClass}>Report volume by hour of day &mdash; reveals when harmful content peaks.</p>
            <HourlyPatternsChart dateRange={dateRange} />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>{t.countyRiskAnalysis}</h2>
            <p className={chartDescClass}>Geographic breakdown of risk levels across Kenyan counties.</p>
            <CountyHeatmap dateRange={dateRange} />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>Detection methods vs risk</h2>
            <p className={chartDescClass}>Which detection methods (Lexicon, Detoxify, Kenyan Model, AI) are triggering at each risk level.</p>
            <DetectionRiskChart dateRange={dateRange} />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>Confidence score distribution</h2>
            <p className={chartDescClass}>Histogram of model confidence scores &mdash; higher confidence means more certain classifications.</p>
            <ConfidenceHistogramChart dateRange={dateRange} />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>URLs &amp; mentions vs risk</h2>
            <p className={chartDescClass}>Relationship between shared URLs/mentions and their associated risk levels.</p>
            <UrlMentionRiskChart dateRange={dateRange} />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>Recent reports</h2>
            <p className={chartDescClass}>The latest reports received, showing risk level and key details.</p>
            <RecentReports />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>Coordinated campaigns</h2>
            <p className={chartDescClass}>Groups of reports from multiple senders sharing the same narrative &mdash; potential coordinated activity.</p>
            <CoordinatedCampaignsWidget />
          </div>
        </div>

        {/* Intelligence section: clusters & lexicon suggestions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>Narrative clusters</h2>
            <p className={chartDescClass}>Automatically discovered themes from report content, grouped by semantic similarity using AI embeddings.</p>
            <TopicClustersWidget />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>Suggested keywords</h2>
            <p className={chartDescClass}>Keywords found frequently in high-risk clusters that aren&apos;t yet in the detection lexicon &mdash; candidates for review.</p>
            <LexiconSuggestionsWidget />
          </div>
        </div>
      </div>
    </div>
  );
}
