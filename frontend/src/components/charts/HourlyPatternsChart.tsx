'use client';

import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { analyticsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface HourlyPatternsChartProps {
  dateRange?: { start_date?: string; end_date?: string };
}

export function HourlyPatternsChart({ dateRange }: HourlyPatternsChartProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'hourly-patterns', dateRange],
    queryFn: () => analyticsApi.getHourlyPatterns(dateRange),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <div className="text-red-600">Error loading data</div>;
  if (!data || !data.patterns) return <div className="text-gray-500">No hourly pattern data available</div>;

  // Convert patterns object to array for chart
  const chartData = Object.entries(data.patterns)
    .map(([hour, values]) => ({
      hour: `${hour.padStart(2, '0')}:00`,
      hourNum: parseInt(hour),
      HIGH: values.HIGH || 0,
      MEDIUM: values.MEDIUM || 0,
      LOW: values.LOW || 0,
    }))
    .sort((a, b) => a.hourNum - b.hourNum);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="hour" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="HIGH" stackId="a" fill="#ef4444" />
        <Bar dataKey="MEDIUM" stackId="a" fill="#f59e0b" />
        <Bar dataKey="LOW" stackId="a" fill="#10b981" />
      </BarChart>
    </ResponsiveContainer>
  );
}
