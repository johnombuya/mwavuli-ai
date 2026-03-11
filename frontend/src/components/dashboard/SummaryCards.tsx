'use client';

import { useQuery } from '@tanstack/react-query';
import { useLanguage } from '@/contexts/LanguageContext';
import { analyticsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { formatNumber } from '@/lib/utils';

interface SummaryCardsProps {
  dateRange?: { start_date?: string; end_date?: string };
}

export function SummaryCards({ dateRange }: SummaryCardsProps) {
  const { t } = useLanguage();
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'summary', dateRange],
    queryFn: () => analyticsApi.getSummary(dateRange),
    staleTime: 2 * 60 * 1000,
  });
  const { data: statusSummary } = useQuery({
    queryKey: ['analytics', 'status-summary', dateRange],
    queryFn: () => analyticsApi.getStatusSummary(dateRange),
    staleTime: 2 * 60 * 1000,
  });

  const cardBase =
    'bg-white rounded-xl border border-slate-200/60 shadow-sm p-6 border-l-4';

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={`${cardBase} border-l-slate-300 animate-pulse`}
          >
            <div className="h-3 bg-slate-200 rounded w-3/4 mb-2 uppercase tracking-wide"></div>
            <div className="h-8 bg-slate-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-4">
        <p className="text-red-800">Error loading summary statistics</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {['Total Reports', 'High Risk', 'Medium Risk', 'Low Risk'].map((label) => (
          <div key={label} className={`${cardBase} border-l-slate-300`}>
            <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-2">
              {label}
            </h3>
            <p className="text-3xl font-bold text-slate-300">&mdash;</p>
          </div>
        ))}
      </div>
    );
  }

  const pendingCount = statusSummary?.counts?.pending ?? 0;
  const reviewedCount = statusSummary?.counts?.reviewed ?? 0;
  const escalatedCount = statusSummary?.counts?.escalated ?? 0;

  const cards = [
    {
      title: t.totalReports,
      value: formatNumber(data.total_reports),
      borderColor: 'border-l-primary-500',
      valueColor: 'text-primary-600',
    },
    {
      title: t.highRisk,
      value: formatNumber(data.risk_distribution?.HIGH ?? 0),
      borderColor: 'border-l-red-500',
      valueColor: 'text-red-600',
    },
    {
      title: t.mediumRisk,
      value: formatNumber(data.risk_distribution?.MEDIUM ?? 0),
      borderColor: 'border-l-amber-500',
      valueColor: 'text-amber-600',
    },
    {
      title: t.lowRisk,
      value: formatNumber(data.risk_distribution?.LOW ?? 0),
      borderColor: 'border-l-green-500',
      valueColor: 'text-green-600',
    },
    {
      title: 'Pending / Reviewed / Escalated',
      value: `${formatNumber(pendingCount)} / ${formatNumber(
        reviewedCount,
      )} / ${formatNumber(escalatedCount)}`,
      borderColor: 'border-l-slate-400',
      valueColor: 'text-slate-700',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.title}
          className={`${cardBase} ${card.borderColor}`}
        >
          <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-2">
            {card.title}
          </h3>
          <p className={`text-3xl font-bold ${card.valueColor}`}>{card.value}</p>
        </div>
      ))}
    </div>
  );
}
