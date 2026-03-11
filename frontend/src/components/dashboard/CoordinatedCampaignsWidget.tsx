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
  sender_hash?: string;
}

interface CampaignData {
  campaigns: CampaignReport[];
  count?: number;
  unique_senders?: number;
  total_flagged?: number;
  risk_breakdown?: Record<string, number>;
}

const riskColor: Record<string, string> = {
  HIGH: 'text-red-600 bg-red-50',
  MEDIUM: 'text-amber-600 bg-amber-50',
  LOW: 'text-green-600 bg-green-50',
};

export function CoordinatedCampaignsWidget() {
  const refetchInterval = useRefetchInterval();
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'coordinated-campaigns'],
    queryFn: async () => {
      const res = await api.get('/v1/analytics/coordinated-campaigns');
      return res.data as CampaignData;
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

  const uniqueSenders = data?.unique_senders ?? new Set(campaigns.map(c => c.sender_hash)).size;
  const riskBreakdown = data?.risk_breakdown;

  return (
    <div>
      {/* Summary bar */}
      <div className="flex flex-wrap gap-3 mb-3">
        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-700">
          {campaigns.length} flagged report{campaigns.length !== 1 ? 's' : ''}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-700">
          {uniqueSenders} unique sender{uniqueSenders !== 1 ? 's' : ''}
        </span>
        {riskBreakdown && Object.entries(riskBreakdown).map(([level, count]) => (
          <span
            key={level}
            className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${riskColor[level] ?? 'text-slate-600 bg-slate-50'}`}
          >
            {count} {level}
          </span>
        ))}
      </div>

      {/* Report list */}
      <ul className="space-y-2 max-h-56 overflow-y-auto">
        {campaigns.slice(0, 10).map((c) => (
          <li key={c.id} className="bg-slate-50 rounded-lg p-2.5 text-xs">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-slate-500">{c.id.slice(0, 10)}...</span>
              {c.county && <span className="text-slate-600">{c.county}</span>}
              {c.risk_level && (
                <span className={`font-semibold ${c.risk_level === 'HIGH' ? 'text-red-600' : c.risk_level === 'MEDIUM' ? 'text-amber-600' : 'text-green-600'}`}>
                  {c.risk_level}
                </span>
              )}
              {c.timestamp && (
                <span className="text-slate-400 ml-auto">
                  {new Date(c.timestamp).toLocaleString()}
                </span>
              )}
            </div>
            {c.text && (
              <p className="text-slate-600 line-clamp-2 mt-1">{c.text}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
