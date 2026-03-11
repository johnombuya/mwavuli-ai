'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi, TopicCluster } from '@/lib/api';
import { useRefetchInterval } from '@/hooks/useRefetchInterval';

const riskColors: Record<string, string> = {
  HIGH: 'bg-red-100 text-red-700',
  MEDIUM: 'bg-amber-100 text-amber-700',
  LOW: 'bg-green-100 text-green-700',
  UNKNOWN: 'bg-slate-100 text-slate-600',
};

function ClusterCard({ cluster }: { cluster: TopicCluster }) {
  const [expanded, setExpanded] = useState(false);
  const risk = cluster.risk_breakdown ?? {};
  const counties = cluster.county_distribution ?? {};
  const keywords = Array.isArray(cluster.top_keywords) ? cluster.top_keywords : [];

  const topCounties = Object.entries(counties)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3);

  const timeRange = cluster.first_seen && cluster.last_seen
    ? `${new Date(cluster.first_seen).toLocaleDateString()} – ${new Date(cluster.last_seen).toLocaleDateString()}`
    : null;

  return (
    <div className="border border-slate-200 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono text-slate-400">Cluster #{cluster.cluster_label}</span>
        <span className="text-xs font-semibold text-slate-700">{cluster.size} reports</span>
      </div>

      {/* Risk breakdown */}
      <div className="flex flex-wrap gap-1.5 mb-2">
        {Object.entries(risk).map(([level, count]) => (
          <span
            key={level}
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${riskColors[level] ?? riskColors.UNKNOWN}`}
          >
            {count} {level}
          </span>
        ))}
      </div>

      {/* Keywords */}
      {keywords.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {keywords.slice(0, 8).map((kw) => (
            <span
              key={kw}
              className="inline-block rounded bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700"
            >
              {kw}
            </span>
          ))}
        </div>
      )}

      {/* Counties */}
      {topCounties.length > 0 && (
        <p className="text-xs text-slate-500 mb-1">
          Counties: {topCounties.map(([c, n]) => `${c} (${n})`).join(', ')}
        </p>
      )}

      {timeRange && (
        <p className="text-xs text-slate-400">{timeRange}</p>
      )}

      {/* Expandable representative text */}
      {cluster.representative_text && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-indigo-600 hover:text-indigo-800 mt-1"
        >
          {expanded ? 'Hide sample' : 'Show sample text'}
        </button>
      )}
      {expanded && cluster.representative_text && (
        <p className="mt-1 text-xs text-slate-600 bg-slate-50 rounded p-2 line-clamp-4">
          {cluster.representative_text}
        </p>
      )}
    </div>
  );
}

export function TopicClustersWidget() {
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

  const clusters = data?.clusters ?? [];
  if (!clusters.length) {
    return (
      <div className="text-sm text-slate-500">
        No narrative clusters detected yet. Run the clustering script to discover patterns.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold text-slate-700">
        {clusters.length} active narrative cluster{clusters.length !== 1 ? 's' : ''}
      </p>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {clusters.map((c) => (
          <ClusterCard key={c.id} cluster={c} />
        ))}
      </div>
    </div>
  );
}
