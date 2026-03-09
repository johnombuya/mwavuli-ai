'use client';

import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';
import { useRefetchInterval } from '@/hooks/useRefetchInterval';

export function DailySummaryCard() {
  const refetchInterval = useRefetchInterval();
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'daily-summary'],
    queryFn: () => analyticsApi.getDailySummary(),
    refetchInterval,
  });

  if (isLoading) {
    return <div className="animate-pulse h-24 rounded-xl bg-slate-100" />;
  }
  if (!data?.summary) return null;

  return (
    <div className="rounded-xl border border-slate-200/60 bg-white shadow-sm p-5">
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">
        Daily summary (24 h)
      </p>
      <p className="text-sm text-slate-800 leading-relaxed">{data.summary}</p>
    </div>
  );
}
