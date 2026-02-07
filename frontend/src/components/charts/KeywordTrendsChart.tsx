'use client';

import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { analyticsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface KeywordTrendsChartProps {
  dateRange?: { start_date?: string; end_date?: string };
}

export function KeywordTrendsChart({ dateRange }: KeywordTrendsChartProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'keyword-trends', dateRange],
    queryFn: () => analyticsApi.getKeywordTrends({ limit: 10, ...dateRange }),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <div className="text-red-600">Error loading data</div>;
  if (!data || data.keywords.length === 0) return <div className="text-gray-500">No keyword data available</div>;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data.keywords} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" />
        <YAxis dataKey="keyword" type="category" width={100} />
        <Tooltip />
        <Legend />
        <Bar dataKey="count" fill="#0284c7" name="Count" />
      </BarChart>
    </ResponsiveContainer>
  );
}
