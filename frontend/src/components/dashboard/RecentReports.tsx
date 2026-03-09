'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { analyticsApi, reportsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import type { RecentReport } from '@/types/api';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  reviewed: 'bg-blue-100 text-blue-800',
  escalated: 'bg-red-100 text-red-800',
};
const RISK_COLORS: Record<string, string> = {
  HIGH: 'text-red-600',
  MEDIUM: 'text-amber-600',
  LOW: 'text-green-600',
};

const ACTION_BUTTONS: { status: string; label: string; cls: string }[] = [
  { status: 'reviewed', label: 'Mark reviewed', cls: 'text-blue-700 hover:bg-blue-50' },
  { status: 'escalated', label: 'Escalate', cls: 'text-red-700 hover:bg-red-50' },
  { status: 'pending', label: 'Reopen', cls: 'text-amber-700 hover:bg-amber-50' },
];

export function RecentReports() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'recent', statusFilter],
    queryFn: () => analyticsApi.getRecentReports({ limit: 15, status: statusFilter || undefined }),
  });

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      reportsApi.updateStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analytics', 'recent'] });
    },
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <div className="text-red-600">Error loading recent reports</div>;
  if (!data?.reports?.length) return <p className="text-gray-500">No reports yet.</p>;

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <label className="text-sm font-medium text-gray-700">Status:</label>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded border border-gray-300 text-sm py-1 px-2"
        >
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="reviewed">Reviewed</option>
          <option value="escalated">Escalated</option>
        </select>
      </div>
      <ul className="space-y-2 max-h-[28rem] overflow-y-auto">
        {data.reports.map((r: RecentReport) => {
          const risk = r.risk_level || 'UNKNOWN';
          const status = r.status || 'pending';
          const timestampLabel = r.timestamp ? new Date(r.timestamp).toLocaleString() : '';

          return (
            <li key={r.id} className="bg-white border border-gray-200 rounded p-3 text-sm">
              <p className="text-gray-900 line-clamp-2">{r.text || '\u2014'}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2 justify-between">
                <div className="flex flex-wrap gap-2 items-center">
                  <span className={RISK_COLORS[risk] || 'text-gray-600'}>{risk}</span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                      STATUS_COLORS[status] || 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {status}
                  </span>
                  {(r as any).recommended_action && (
                    <span className="rounded px-1.5 py-0.5 text-xs font-medium bg-indigo-50 text-indigo-700">
                      {(r as any).recommended_action}
                    </span>
                  )}
                </div>
                {timestampLabel && (
                  <span className="text-xs text-gray-500">{timestampLabel}</span>
                )}
              </div>
              {/* Moderation actions */}
              <div className="mt-2 flex gap-1 border-t border-gray-100 pt-2">
                {ACTION_BUTTONS.filter((a) => a.status !== status).map((a) => (
                  <button
                    key={a.status}
                    disabled={mutation.isPending}
                    onClick={() => mutation.mutate({ id: r.id, status: a.status })}
                    className={`rounded px-2 py-1 text-xs font-medium transition-colors ${a.cls}`}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
