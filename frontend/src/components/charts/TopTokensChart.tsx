'use client';

import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { analyticsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface TopTokensChartProps {
  dateRange?: { start_date?: string; end_date?: string };
}

export function TopTokensChart({ dateRange }: TopTokensChartProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'top-tokens', dateRange],
    queryFn: () => analyticsApi.getTopTokens({ limit: 15, risk_levels: 'HIGH', ...dateRange }),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <div className="text-red-600">Error loading data</div>;
  if (!data || data.tokens.length === 0) {
    return (
      <div className="text-gray-500">
        No token trends yet. This chart updates from the words used in recent high-risk reports.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data.tokens} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" />
        <YAxis dataKey="token" type="category" width={140} />
        <Tooltip />
        <Legend />
        <Bar dataKey="count" fill="#16a34a" name="Token frequency" />
      </BarChart>
    </ResponsiveContainer>
  );
}

