'use client';

import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { useRefetchInterval } from '@/hooks/useRefetchInterval';

interface EscalatedReport {
  id: string;
  text?: string;
  county?: string;
  risk_level?: string;
  timestamp?: string;
  sector?: string;
}

const riskStyle: Record<string, string> = {
  HIGH: 'text-red-600 bg-red-50',
  MEDIUM: 'text-amber-600 bg-amber-50',
  LOW: 'text-green-600 bg-green-50',
};

export function RecentEscalations() {
  const refetchInterval = useRefetchInterval();

  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'recent-escalated'],
    queryFn: async () => {
      const res = await api.get('/v1/analytics/recent', {
        params: { status_filter: 'escalated', limit: 5 },
      });
      return res.data as { reports: EscalatedReport[]; count: number };
    },
    refetchInterval,
    staleTime: 2 * 60 * 1000,
  });

  if (isLoading) {
    return <div className="animate-pulse h-24 rounded-xl bg-slate-100" />;
  }

  const reports = data?.reports ?? [];

  if (reports.length === 0) {
    return (
      <p className="text-sm text-slate-500">No reports have been escalated in this period.</p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
        {reports.length} escalated report{reports.length !== 1 ? 's' : ''}
      </p>
      <ul className="space-y-2 max-h-64 overflow-y-auto">
        {reports.map((r) => (
          <li key={r.id} className="bg-slate-50 rounded-lg p-3 text-xs">
            <div className="flex items-center gap-2 mb-1">
              {r.risk_level && (
                <span className={`font-semibold rounded-full px-2 py-0.5 ${riskStyle[r.risk_level] ?? 'text-slate-600 bg-slate-100'}`}>
                  {r.risk_level}
                </span>
              )}
              {r.county && r.county !== 'unknown' && (
                <span className="text-slate-600">{r.county}</span>
              )}
              {r.sector && (
                <span className="text-slate-400 capitalize">{r.sector}</span>
              )}
              {r.timestamp && (
                <span className="text-slate-400 ml-auto">
                  {new Date(r.timestamp).toLocaleString()}
                </span>
              )}
            </div>
            {r.text && (
              <p className="text-slate-600 line-clamp-2 mt-1">{r.text}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
