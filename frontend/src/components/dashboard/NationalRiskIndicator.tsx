'use client';

import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';
import { useRefetchInterval } from '@/hooks/useRefetchInterval';

const colorMap: Record<string, { bg: string; text: string; ring: string; label: string }> = {
  RED: { bg: 'bg-red-100', text: 'text-red-700', ring: 'ring-red-400', label: 'HIGH ALERT' },
  AMBER: { bg: 'bg-amber-100', text: 'text-amber-700', ring: 'ring-amber-400', label: 'ELEVATED' },
  GREEN: { bg: 'bg-green-100', text: 'text-green-700', ring: 'ring-green-400', label: 'NORMAL' },
};

export function NationalRiskIndicator() {
  const refetchInterval = useRefetchInterval();
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'national-risk-level'],
    queryFn: () => analyticsApi.getNationalRiskLevel(),
    refetchInterval,
    staleTime: 2 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse h-20 rounded-xl bg-slate-100" />
    );
  }

  if (!data || (data.total_reports <= 1 && data.high_pct === 0 && data.medium_pct === 0)) {
    return (
      <div className="bg-slate-100 text-slate-600 rounded-xl ring-2 ring-slate-300 p-5 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest opacity-70">National risk status</p>
          <p className="text-2xl font-bold mt-1">NO DATA</p>
        </div>
        <div className="text-right text-sm opacity-80">
          <p>No reports in the last 24 hours</p>
        </div>
      </div>
    );
  }

  const style = colorMap[data.level] ?? colorMap.GREEN;

  return (
    <div className={`${style.bg} ${style.text} rounded-xl ring-2 ${style.ring} p-5 flex items-center justify-between`}>
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest opacity-70">National risk status</p>
        <p className="text-2xl font-bold mt-1">{style.label}</p>
      </div>
      <div className="text-right text-sm opacity-80">
        <p>{data.high_pct}% HIGH &middot; {data.medium_pct}% MEDIUM</p>
        <p>{data.total_reports} reports (24 h)</p>
      </div>
    </div>
  );
}
