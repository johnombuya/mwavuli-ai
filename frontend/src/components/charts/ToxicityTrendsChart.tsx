'use client';

import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { analyticsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface ToxicityTrendsChartProps {
  dateRange?: { start_date?: string; end_date?: string };
}

export function ToxicityTrendsChart({ dateRange }: ToxicityTrendsChartProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'toxicity-trends', dateRange],
    queryFn: () => analyticsApi.getToxicityTrends({ days: 30, ...dateRange }),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <div className="text-red-600">Error loading data</div>;
  if (!data || data.trends.length === 0) return <div className="text-gray-500">No toxicity trend data available</div>;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data.trends}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis domain={[0, 1]} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="avg_toxicity" stroke="#dc2626" strokeWidth={2} name="Avg Toxicity" />
      </LineChart>
    </ResponsiveContainer>
  );
}
