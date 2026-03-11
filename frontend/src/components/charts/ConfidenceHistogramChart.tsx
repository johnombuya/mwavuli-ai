'use client';

import { useQuery } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { analyticsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface ConfidenceHistogramChartProps {
  dateRange?: { start_date?: string; end_date?: string };
}

export function ConfidenceHistogramChart({
  dateRange,
}: ConfidenceHistogramChartProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'confidence-histogram', dateRange],
    queryFn: () =>
      analyticsApi.getConfidenceHistogram({
        bucket_size: 0.1,
        ...dateRange,
      }),
    staleTime: 2 * 60 * 1000,
  });

  if (isLoading) return <LoadingSpinner />;
  if (error)
    return <div className="text-red-600">Error loading data</div>;
  if (!data || data.buckets.length === 0) {
    return (
      <div className="text-gray-500">
        No confidence score data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data.buckets}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="bucket" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="count" fill="#4b5563" name="Reports" />
      </BarChart>
    </ResponsiveContainer>
  );
}

