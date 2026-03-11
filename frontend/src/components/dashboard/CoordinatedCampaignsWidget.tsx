'use client';

import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { useRefetchInterval } from '@/hooks/useRefetchInterval';

interface CampaignReport {
  id: string;
  county?: string;
  timestamp?: string;
  risk_level?: string;
  text?: string;
}

export function CoordinatedCampaignsWidget() {
  const refetchInterval = useRefetchInterval();
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'coordinated-campaigns'],
    queryFn: async () => {
      const res = await api.get('/v1/analytics/coordinated-campaigns');
      return res.data as { campaigns: CampaignReport[]; count: number };
    },
    refetchInterval,
    staleTime: 2 * 60 * 1000,
  });

  if (isLoading) {
    return <div className="animate-pulse h-20 rounded-xl bg-slate-100" />;
  }

  const campaigns = data?.campaigns ?? [];
  if (!campaigns.length) {
    return (
      <div className="text-sm text-slate-500">No coordinated campaigns detected.</div>
    );
  }

  return (
    <div>
      <p className="text-sm font-semibold text-slate-700 mb-2">
        {campaigns.length} flagged report{campaigns.length !== 1 ? 's' : ''}
      </p>
      <ul className="space-y-2 max-h-48 overflow-y-auto">
        {campaigns.slice(0, 10).map((c) => (
          <li key={c.id} className="bg-slate-50 rounded p-2 text-xs">
            <span className="font-mono text-slate-500">{c.id.slice(0, 10)}...</span>
            {c.county && <span className="ml-2 text-slate-600">{c.county}</span>}
            {c.risk_level && (
              <span className={`ml-2 font-semibold ${c.risk_level === 'HIGH' ? 'text-red-600' : 'text-amber-600'}`}>
                {c.risk_level}
              </span>
            )}
            {c.timestamp && (
              <span className="ml-2 text-slate-400">
                {new Date(c.timestamp).toLocaleString()}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
