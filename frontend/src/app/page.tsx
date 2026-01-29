'use client';

import { SummaryCards } from '@/components/dashboard/SummaryCards';
import { RiskDistributionChart } from '@/components/charts/RiskDistributionChart';
import { KeywordTrendsChart } from '@/components/charts/KeywordTrendsChart';
import { ToxicityTrendsChart } from '@/components/charts/ToxicityTrendsChart';
import { HourlyPatternsChart } from '@/components/charts/HourlyPatternsChart';
import { CountyHeatmap } from '@/components/dashboard/CountyHeatmap';
import { DateRangePicker } from '@/components/ui/DateRangePicker';
import { useState } from 'react';

export default function DashboardPage() {
  const [dateRange, setDateRange] = useState<{
    start_date?: string;
    end_date?: string;
  }>({});

  return (
    <main className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Mwavuli Analytics Dashboard
          </h1>
          <p className="text-gray-600">
            Real-time content verification analytics and insights
          </p>
        </div>

        {/* Date Range Picker */}
        <div className="mb-6">
          <DateRangePicker
            onDateChange={setDateRange}
            startDate={dateRange.start_date}
            endDate={dateRange.end_date}
          />
        </div>

        {/* Summary Cards */}
        <div className="mb-8">
          <SummaryCards dateRange={dateRange} />
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Risk Distribution */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Risk Distribution</h2>
            <RiskDistributionChart dateRange={dateRange} />
          </div>

          {/* Keyword Trends */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Top Keywords</h2>
            <KeywordTrendsChart dateRange={dateRange} />
          </div>
        </div>

        {/* Full Width Charts */}
        <div className="grid grid-cols-1 gap-6 mb-8">
          {/* Toxicity Trends */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Toxicity Trends</h2>
            <ToxicityTrendsChart dateRange={dateRange} />
          </div>

          {/* Hourly Patterns */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Hourly Patterns</h2>
            <HourlyPatternsChart dateRange={dateRange} />
          </div>

          {/* County Heatmap */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">County Risk Analysis</h2>
            <CountyHeatmap dateRange={dateRange} />
          </div>
        </div>
      </div>
    </main>
  );
}
