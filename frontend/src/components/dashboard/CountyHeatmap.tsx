'use client';

import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { analyticsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface CountyHeatmapProps {
  dateRange?: { start_date?: string; end_date?: string };
}

export function CountyHeatmap({ dateRange }: CountyHeatmapProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'geographic-heatmap', dateRange],
    queryFn: () => analyticsApi.getGeographicHeatmap(dateRange),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <div className="text-red-600">Error loading data</div>;
  if (!data || !data.counties) return <div className="text-gray-500">No county data available</div>;

  // Convert counties object to array and sort by risk score
  const chartData = Object.entries(data.counties)
    .map(([county, values]) => ({
      county,
      riskScore: values.risk_score,
      high: values.HIGH,
      medium: values.MEDIUM,
      low: values.LOW,
    }))
    .sort((a, b) => b.riskScore - a.riskScore)
    .slice(0, 15); // Top 15 counties

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" />
        <YAxis dataKey="county" type="category" width={120} />
        <Tooltip />
        <Legend />
        <Bar dataKey="high" stackId="a" fill="#ef4444" name="High Risk" />
        <Bar dataKey="medium" stackId="a" fill="#f59e0b" name="Medium Risk" />
        <Bar dataKey="low" stackId="a" fill="#10b981" name="Low Risk" />
      </BarChart>
    </ResponsiveContainer>
  );
}
