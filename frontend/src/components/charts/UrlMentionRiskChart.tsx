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

interface UrlMentionRiskChartProps {
  dateRange?: { start_date?: string; end_date?: string };
}

export function UrlMentionRiskChart({
  dateRange,
}: UrlMentionRiskChartProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'url-mention-risk', dateRange],
    queryFn: () => analyticsApi.getUrlMentionRisk(dateRange),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error)
    return <div className="text-red-600">Error loading data</div>;
  if (!data || !data.stats) {
    return (
      <div className="text-gray-500">
        No URL/mention data available
      </div>
    );
  }

  const { with_urls, without_urls, with_mentions, without_mentions } =
    data.stats;

  const chartData = [
    {
      group: 'With URLs',
      HIGH: with_urls.HIGH ?? 0,
      MEDIUM: with_urls.MEDIUM ?? 0,
      LOW: with_urls.LOW ?? 0,
    },
    {
      group: 'No URLs',
      HIGH: without_urls.HIGH ?? 0,
      MEDIUM: without_urls.MEDIUM ?? 0,
      LOW: without_urls.LOW ?? 0,
    },
    {
      group: 'With mentions',
      HIGH: with_mentions.HIGH ?? 0,
      MEDIUM: with_mentions.MEDIUM ?? 0,
      LOW: with_mentions.LOW ?? 0,
    },
    {
      group: 'No mentions',
      HIGH: without_mentions.HIGH ?? 0,
      MEDIUM: without_mentions.MEDIUM ?? 0,
      LOW: without_mentions.LOW ?? 0,
    },
  ];

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="group" />
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

