'use client';

import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';
import { useRefetchInterval } from '@/hooks/useRefetchInterval';

interface ExecSummaryData {
  summary: string;
  generated_at: string;
  data: {
    threat_level: string;
    total_reports: number;
    high_pct: number;
    medium_pct: number;
    risk_distribution: Record<string, number>;
    top_counties: string;
    coordinated_campaigns: number;
    narrative_clusters: string;
    top_keywords: string;
  };
}

function FallbackSummary({ data }: { data: ExecSummaryData['data'] }) {
  return (
    <div className="text-sm text-slate-700 leading-relaxed space-y-1">
      <p>
        <strong>{data.total_reports}</strong> reports analyzed in the last 24 hours.
        Threat level: <strong>{data.threat_level}</strong>.
      </p>
      <p>
        Risk breakdown: {data.risk_distribution?.HIGH ?? 0} HIGH,{' '}
        {data.risk_distribution?.MEDIUM ?? 0} MEDIUM,{' '}
        {data.risk_distribution?.LOW ?? 0} LOW.
      </p>
      {data.top_counties && data.top_counties !== 'none' && (
        <p>Most active counties: {data.top_counties}.</p>
      )}
      {data.coordinated_campaigns > 0 && (
        <p>{data.coordinated_campaigns} coordinated campaign{data.coordinated_campaigns !== 1 ? 's' : ''} detected.</p>
      )}
    </div>
  );
}

export function ExecutiveSummary() {
  const refetchInterval = useRefetchInterval();

  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'executive-summary'],
    queryFn: async () => {
      const res = await analyticsApi.getExecutiveSummary();
      return res as ExecSummaryData;
    },
    refetchInterval,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-6">
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-slate-100 rounded w-1/3" />
          <div className="h-3 bg-slate-100 rounded w-full" />
          <div className="h-3 bg-slate-100 rounded w-5/6" />
          <div className="h-3 bg-slate-100 rounded w-4/6" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-50 to-white rounded-xl border border-slate-200/60 shadow-sm p-6">
      <h2 className="text-lg font-semibold text-slate-900 mb-3">Executive Brief</h2>

      {error || !data?.summary ? (
        data?.data ? (
          <FallbackSummary data={data.data} />
        ) : (
          <p className="text-sm text-slate-500">Unable to generate executive summary at this time.</p>
        )
      ) : (
        <p className="text-sm text-slate-700 leading-relaxed">{data.summary}</p>
      )}

      {data?.generated_at && (
        <p className="text-xs text-slate-400 mt-3">
          Generated {new Date(data.generated_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}
