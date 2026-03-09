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
  });

  if (isLoading || !data) {
    return (
      <div className="animate-pulse h-20 rounded-xl bg-slate-100" />
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
