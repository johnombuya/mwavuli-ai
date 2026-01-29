'use client';

import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { formatNumber } from '@/lib/utils';

interface SummaryCardsProps {
  dateRange?: { start_date?: string; end_date?: string };
}

export function SummaryCards({ dateRange }: SummaryCardsProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'summary', dateRange],
    queryFn: () => analyticsApi.getSummary(dateRange),
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error loading summary statistics</p>
      </div>
    );
  }

  if (!data) return null;

  const cards = [
    {
      title: 'Total Reports',
      value: formatNumber(data.total_reports),
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'High Risk',
      value: formatNumber(data.risk_distribution.HIGH),
      color: 'text-red-600',
      bgColor: 'bg-red-50',
    },
    {
      title: 'Medium Risk',
      value: formatNumber(data.risk_distribution.MEDIUM),
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
    },
    {
      title: 'Low Risk',
      value: formatNumber(data.risk_distribution.LOW),
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.title}
          className={`${card.bgColor} rounded-lg shadow p-6 border-l-4 ${card.color.replace('text-', 'border-')}`}
        >
          <h3 className="text-sm font-medium text-gray-600 mb-2">{card.title}</h3>
          <p className={`text-3xl font-bold ${card.color}`}>{card.value}</p>
        </div>
      ))}
    </div>
  );
}
