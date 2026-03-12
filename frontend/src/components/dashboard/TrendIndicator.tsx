'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';
import { useRefetchInterval } from '@/hooks/useRefetchInterval';

interface ToxicityPoint {
  date: string;
  avg_toxicity: number;
  count: number;
}

export function TrendIndicator() {
  const refetchInterval = useRefetchInterval();

  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'toxicity-trends', { days: 14 }],
    queryFn: () => analyticsApi.getToxicityTrends({ days: 14 }),
    refetchInterval,
    staleTime: 5 * 60 * 1000,
  });

  const trend = useMemo(() => {
    const points: ToxicityPoint[] = data?.trends ?? [];
    if (points.length < 4) return null;

    const sorted = [...points].sort((a, b) => a.date.localeCompare(b.date));
    const mid = Math.floor(sorted.length / 2);
    const older = sorted.slice(0, mid);
    const recent = sorted.slice(mid);

    const avg = (arr: ToxicityPoint[]) => {
      const total = arr.reduce((s, p) => s + p.avg_toxicity * p.count, 0);
      const count = arr.reduce((s, p) => s + p.count, 0);
      return count > 0 ? total / count : 0;
    };

    const olderAvg = avg(older);
    const recentAvg = avg(recent);

    if (olderAvg === 0) return { direction: 'flat' as const, pct: 0, recentAvg, olderAvg };

    const pctChange = ((recentAvg - olderAvg) / olderAvg) * 100;

    let direction: 'up' | 'down' | 'flat';
    if (pctChange > 5) direction = 'up';
    else if (pctChange < -5) direction = 'down';
    else direction = 'flat';

    return { direction, pct: Math.abs(Math.round(pctChange)), recentAvg, olderAvg };
  }, [data]);

  if (isLoading) {
    return <div className="animate-pulse h-16 rounded-xl bg-slate-100" />;
  }

  if (!trend) {
    return (
      <p className="text-sm text-slate-500">Not enough data to calculate trend (need at least 4 days).</p>
    );
  }

  const config = {
    up: {
      icon: '↑',
      bg: 'bg-red-50',
      text: 'text-red-700',
      ring: 'ring-red-200',
      message: `Content severity increased ${trend.pct}% compared to last week.`,
    },
    down: {
      icon: '↓',
      bg: 'bg-green-50',
      text: 'text-green-700',
      ring: 'ring-green-200',
      message: `Harmful content is decreasing — down ${trend.pct}% from last week.`,
    },
    flat: {
      icon: '→',
      bg: 'bg-slate-50',
      text: 'text-slate-700',
      ring: 'ring-slate-200',
      message: 'Content severity is stable compared to last week.',
    },
  };

  const c = config[trend.direction];

  return (
    <div className={`${c.bg} ${c.text} rounded-xl ring-1 ${c.ring} p-4 flex items-center gap-4`}>
      <span className="text-3xl font-bold">{c.icon}</span>
      <div>
        <p className="text-sm font-semibold">Is it getting better or worse?</p>
        <p className="text-sm opacity-80">{c.message}</p>
      </div>
    </div>
  );
}
