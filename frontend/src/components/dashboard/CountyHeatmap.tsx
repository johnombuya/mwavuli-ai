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

  type CountyValues = { risk_score: number; HIGH: number; MEDIUM: number; LOW: number };
  const chartData = Object.entries(data.counties)
    // Filter out \"unknown\" pseudo-county to focus on real locations
    .filter(([county]) => county.toLowerCase() !== 'unknown')
    .map(([county, values]) => {
      const v = values as CountyValues;
      return {
        county,
        riskScore: v.risk_score,
        high: v.HIGH,
        medium: v.MEDIUM,
        low: v.LOW,
      };
    })
    .sort((a, b) => b.riskScore - a.riskScore)
    .slice(0, 15); // Top 15 counties

  if (chartData.length === 0) {
    return <div className="text-gray-500">Only reports without county metadata so far.</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" />
        <YAxis dataKey="county" type="category" width={120} />
        <Tooltip />
        <Legend />
        <Bar dataKey="high" stackId="a" fill="#dc2626" name="High Risk" />
        <Bar dataKey="medium" stackId="a" fill="#d97706" name="Medium Risk" />
        <Bar dataKey="low" stackId="a" fill="#059669" name="Low Risk" />
      </BarChart>
    </ResponsiveContainer>
  );
}
