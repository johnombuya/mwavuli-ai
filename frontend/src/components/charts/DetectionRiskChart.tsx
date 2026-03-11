'use client';

import { useQuery } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { analyticsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface DetectionRiskChartProps {
  dateRange?: { start_date?: string; end_date?: string };
}

export function DetectionRiskChart({ dateRange }: DetectionRiskChartProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'detection-risk-matrix', dateRange],
    queryFn: () => analyticsApi.getDetectionRiskMatrix(dateRange),
    staleTime: 2 * 60 * 1000,
  });

  if (isLoading) return <LoadingSpinner />;
  if (error)
    return <div className="text-red-600">Error loading data</div>;
  if (!data || !data.matrix)
    return (
      <div className="text-gray-500">
        No detection method data available
      </div>
    );

  const chartData = Object.entries(data.matrix).map(
    ([method, counts]) => ({
      method,
      HIGH: counts.HIGH ?? 0,
      MEDIUM: counts.MEDIUM ?? 0,
      LOW: counts.LOW ?? 0,
    }),
  );

  if (chartData.length === 0) {
    return (
      <div className="text-gray-500">
        No detection method data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="method" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="HIGH" stackId="a" fill="#dc2626" name="High" />
        <Bar
          dataKey="MEDIUM"
          stackId="a"
          fill="#d97706"
          name="Medium"
        />
        <Bar dataKey="LOW" stackId="a" fill="#059669" name="Low" />
      </BarChart>
    </ResponsiveContainer>
  );
}

