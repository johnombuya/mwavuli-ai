'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reportsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  resolved: 'bg-green-100 text-green-800',
};

const RISK_COLORS: Record<string, string> = {
  HIGH: 'text-red-600 bg-red-50',
  MEDIUM: 'text-amber-600 bg-amber-50',
  LOW: 'text-green-600 bg-green-50',
};

interface Appeal {
  appeal_id: string;
  report_id: string;
  reason: string;
  status: string;
  timestamp: string;
  original_risk_level?: string;
  resolution?: string;
  resolved_at?: string;
  notes?: string;
}

export default function AppealsPage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<string>('pending');

  const { data, isLoading, error } = useQuery({
    queryKey: ['appeals', filter],
    queryFn: () => reportsApi.getAppeals({ status: filter || undefined }),
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, resolution, notes }: { id: string; resolution: string; notes?: string }) =>
      reportsApi.resolveAppeal(id, { resolution, notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appeals'] });
      queryClient.invalidateQueries({ queryKey: ['analytics', 'recent'] });
    },
  });

  return (
    <div className="p-6 md:p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Appeals</h1>
          <p className="text-slate-600">
            Review and resolve appeals submitted against flagged reports.
          </p>
        </div>

        <div className="flex items-center gap-3 mb-6">
          <label className="text-sm font-medium text-slate-700">Filter:</label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="rounded-lg border border-slate-300 text-sm py-2 px-3"
          >
            <option value="pending">Pending</option>
            <option value="resolved">Resolved</option>
            <option value="">All</option>
          </select>
        </div>

        {isLoading && <LoadingSpinner />}
        {error && <p className="text-red-600">Failed to load appeals.</p>}

        {data && !data.appeals?.length && (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500">
            No {filter || ''} appeals found.
          </div>
        )}

        {data?.appeals?.length > 0 && (
          <div className="space-y-4">
            {data.appeals.map((a: Appeal) => (
              <div
                key={a.appeal_id}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-semibold ${
                        STATUS_COLORS[a.status] || 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {a.status}
                    </span>
                    {a.original_risk_level && (
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-semibold ${
                          RISK_COLORS[a.original_risk_level] || 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        Original: {a.original_risk_level}
                      </span>
                    )}
                    <span className="text-xs text-slate-500">
                      Report: <code className="font-mono">{a.report_id?.slice(0, 12)}...</code>
                    </span>
                  </div>
                  <span className="text-xs text-slate-400">
                    {a.timestamp ? new Date(a.timestamp).toLocaleString() : ''}
                  </span>
                </div>

                <p className="text-sm text-slate-800 mb-3">{a.reason}</p>

                {a.resolution && (
                  <p className="text-sm text-slate-600 mb-2">
                    Resolution: <strong>{a.resolution}</strong>
                    {a.notes && <> &mdash; {a.notes}</>}
                  </p>
                )}

                {a.status === 'pending' && (
                  <div className="flex gap-2 border-t border-slate-100 pt-3 mt-2">
                    <button
                      disabled={resolveMutation.isPending}
                      onClick={() =>
                        resolveMutation.mutate({ id: a.appeal_id, resolution: 'upheld' })
                      }
                      className="rounded-lg px-3 py-1.5 text-xs font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
                    >
                      Uphold (keep flagged)
                    </button>
                    <button
                      disabled={resolveMutation.isPending}
                      onClick={() =>
                        resolveMutation.mutate({ id: a.appeal_id, resolution: 'overturned' })
                      }
                      className="rounded-lg px-3 py-1.5 text-xs font-medium bg-green-50 text-green-700 hover:bg-green-100 transition-colors"
                    >
                      Overturn (mark reviewed)
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
