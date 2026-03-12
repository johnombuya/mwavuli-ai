'use client';

import { useQuery } from '@tanstack/react-query';
import { analyticsApi, TopicCluster } from '@/lib/api';
import { useRefetchInterval } from '@/hooks/useRefetchInterval';

const riskBadge: Record<string, string> = {
  HIGH: 'bg-red-100 text-red-700',
  MEDIUM: 'bg-amber-100 text-amber-700',
  LOW: 'bg-green-100 text-green-700',
};

function dominantRisk(breakdown: Record<string, number>): string {
  let best = 'LOW';
  let bestN = 0;
  for (const [level, n] of Object.entries(breakdown)) {
    if (n > bestN) {
      best = level;
      bestN = n;
    }
  }
  return best;
}

function ThreatCard({ cluster }: { cluster: TopicCluster }) {
  const risk = cluster.risk_breakdown ?? {};
  const counties = cluster.county_distribution ?? {};
  const keywords = Array.isArray(cluster.top_keywords) ? cluster.top_keywords : [];
  const topCounties = Object.entries(counties)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)
    .map(([c]) => c);

  const title = keywords.length > 0
    ? keywords.slice(0, 3).join(', ') + ' narrative'
    : `Cluster #${cluster.cluster_label}`;

  const riskLevel = dominantRisk(risk);

  const timeRange = cluster.first_seen && cluster.last_seen
    ? `${new Date(cluster.first_seen).toLocaleDateString()} – ${new Date(cluster.last_seen).toLocaleDateString()}`
    : null;

  return (
    <div className="border border-slate-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-900 capitalize leading-tight">{title}</h3>
        <span className={`ml-2 shrink-0 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${riskBadge[riskLevel] ?? 'bg-slate-100 text-slate-600'}`}>
          {riskLevel}
        </span>
      </div>

      <div className="text-xs text-slate-600 space-y-1">
        <p>
          <span className="font-medium">{cluster.size}</span> reports
          {topCounties.length > 0 && (
            <> — affecting <span className="font-medium">{topCounties.join(', ')}</span></>
          )}
        </p>
        {timeRange && <p className="text-slate-400">{timeRange}</p>}
      </div>

      {cluster.representative_text && (
        <p className="mt-2 text-xs text-slate-500 line-clamp-2 italic">
          &ldquo;{cluster.representative_text}&rdquo;
        </p>
      )}
    </div>
  );
}

export function TopThreatsCard() {
  const refetchInterval = useRefetchInterval();

  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'topic-clusters'],
    queryFn: () => analyticsApi.getTopicClusters(),
    refetchInterval,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return <div className="animate-pulse h-32 rounded-xl bg-slate-100" />;
  }

  const clusters = (data?.clusters ?? [])
    .sort((a: TopicCluster, b: TopicCluster) => {
      const aHigh = (a.risk_breakdown?.HIGH ?? 0);
      const bHigh = (b.risk_breakdown?.HIGH ?? 0);
      return bHigh - aHigh;
    })
    .slice(0, 3);

  if (clusters.length === 0) {
    return (
      <p className="text-sm text-slate-500">No active threats detected. Run the clustering pipeline to discover narrative patterns.</p>
    );
  }

  return (
    <div className="space-y-3">
      {clusters.map((c: TopicCluster) => (
        <ThreatCard key={c.id} cluster={c} />
      ))}
    </div>
  );
}
