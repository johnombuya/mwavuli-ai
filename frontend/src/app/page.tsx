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

const chartCardClass =
  'bg-white rounded-xl border border-slate-200/60 shadow-sm p-6';
const chartTitleClass = 'text-xl font-semibold text-slate-900 mb-4';

export default function DashboardPage() {
  const { t } = useLanguage();
  const [dateRange, setDateRange] = useState<{
    start_date?: string;
    end_date?: string;
  }>({});

  return (
    <div className="p-6 md:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">
            {t.dashboardTitle}
          </h1>
          <p className="text-slate-600">
            {t.dashboardSubtitle}
          </p>
        </div>

        {/* Date Range Picker and Export */}
        <div className="mb-6 flex flex-wrap items-center gap-4">
          <DateRangePicker
            onDateChange={setDateRange}
            startDate={dateRange.start_date}
            endDate={dateRange.end_date}
          />
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

        {/* Summary Cards */}
        <div className="mb-8">
          <SummaryCards dateRange={dateRange} />
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>{t.riskDistribution}</h2>
            <RiskDistributionChart dateRange={dateRange} />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>{t.topKeywords}</h2>
            <KeywordTrendsChart dateRange={dateRange} />
            <div className="mt-4 border-t pt-4 text-sm text-slate-600">
              <p className="font-medium mb-2">Top tokens in high-risk reports</p>
              <TopTokensChart dateRange={dateRange} />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 mb-8">
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>{t.toxicityTrends}</h2>
            <ToxicityTrendsChart dateRange={dateRange} />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>{t.hourlyPatterns}</h2>
            <HourlyPatternsChart dateRange={dateRange} />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>{t.countyRiskAnalysis}</h2>
            <CountyHeatmap dateRange={dateRange} />
          </div>
          <div className={chartCardClass}>
            <h2 className={chartTitleClass}>Recent reports</h2>
            <RecentReports />
          </div>
        </div>
      </div>
    </div>
  );
}
