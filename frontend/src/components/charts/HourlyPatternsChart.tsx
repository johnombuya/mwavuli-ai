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
    staleTime: 2 * 60 * 1000,
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <div className="text-red-600">Error loading data</div>;
  if (!data || !data.patterns) return <div className="text-gray-500">No hourly pattern data available</div>;

  // Convert patterns object to array for chart
  const chartData = Object.entries(data.patterns)
    .map(([hour, values]) => {
      const v = values as { HIGH?: number; MEDIUM?: number; LOW?: number };
      return {
        hour: `${hour.padStart(2, '0')}:00`,
        hourNum: parseInt(hour),
        HIGH: v.HIGH ?? 0,
        MEDIUM: v.MEDIUM ?? 0,
        LOW: v.LOW ?? 0,
      };
    })
    .sort((a, b) => a.hourNum - b.hourNum);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="hour" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="HIGH" stackId="a" fill="#dc2626" />
        <Bar dataKey="MEDIUM" stackId="a" fill="#d97706" />
        <Bar dataKey="LOW" stackId="a" fill="#059669" />
      </BarChart>
    </ResponsiveContainer>
  );
}
