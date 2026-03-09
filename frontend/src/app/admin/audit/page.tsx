'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface AuditEntry {
  id: string;
  timestamp: string;
  action: string;
  user_id: string;
  details?: Record<string, unknown>;
  api_key_hash?: string;
}

export default function AuditLogPage() {
  const [actionFilter, setActionFilter] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['admin', 'audit-logs', actionFilter],
    queryFn: async () => {
      const params: Record<string, string | number> = { limit: 100 };
      if (actionFilter) params.action = actionFilter;
      const res = await api.get('/v1/admin/audit-logs', { params });
      return res.data as { logs: AuditEntry[]; count: number };
    },
  });

  return (
    <div className="p-6 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Audit log</h1>
          <p className="text-slate-600">
            Immutable record of significant system actions.
          </p>
        </div>

        <div className="flex items-center gap-3 mb-6">
          <label className="text-sm font-medium text-slate-700">Action:</label>
          <input
            type="text"
            placeholder="e.g. update_report_status"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="rounded-lg border border-slate-300 text-sm py-2 px-3 w-64"
          />
        </div>

        {isLoading && <LoadingSpinner />}
        {error && <p className="text-red-600">Failed to load audit logs.</p>}

        {data && !data.logs?.length && (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500">
            No audit log entries found.
          </div>
        )}

        {data?.logs && data.logs.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="text-left px-4 py-3 font-semibold text-slate-700">Time</th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-700">Action</th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-700">User</th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-700">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.logs.map((entry) => (
                  <tr key={entry.id} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 text-slate-500 whitespace-nowrap">
                      {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : '\u2014'}
                    </td>
                    <td className="px-4 py-2.5">
                      <code className="text-xs bg-slate-100 rounded px-1.5 py-0.5 font-mono">
                        {entry.action}
                      </code>
                    </td>
                    <td className="px-4 py-2.5 text-slate-600">{entry.user_id}</td>
                    <td className="px-4 py-2.5 text-slate-500 text-xs max-w-xs truncate">
                      {entry.details ? JSON.stringify(entry.details) : '\u2014'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
