'use client';

import { useQuery } from '@tanstack/react-query';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { analyticsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface RiskDistributionChartProps {
  dateRange?: { start_date?: string; end_date?: string };
}

const COLORS = {
  HIGH: '#dc2626',
  MEDIUM: '#d97706',
  LOW: '#059669',
  UNKNOWN: '#64748b',
};

export function RiskDistributionChart({ dateRange }: RiskDistributionChartProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'risk-distribution', dateRange],
    queryFn: () => analyticsApi.getRiskDistribution(dateRange),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <div className="text-red-600">Error loading data</div>;
  if (!data) return null;

  const chartData = Object.entries(data.distribution)
    .filter(([, value]) => (value as number) > 0)
    .map(([name, value]) => ({
      name,
      value: value as number,
    }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[entry.name as keyof typeof COLORS] || COLORS.UNKNOWN} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
