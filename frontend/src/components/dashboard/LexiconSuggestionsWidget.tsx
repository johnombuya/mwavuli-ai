'use client';

import { useQuery } from '@tanstack/react-query';
import { analyticsApi, LexiconSuggestion } from '@/lib/api';
import { useRefetchInterval } from '@/hooks/useRefetchInterval';

function SuggestionRow({ suggestion }: { suggestion: LexiconSuggestion }) {
  const highPct = suggestion.total_reports > 0
    ? Math.round((suggestion.high_reports / suggestion.total_reports) * 100)
    : 0;

  return (
    <li className="flex items-start gap-3 py-2 border-b border-slate-100 last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm text-slate-800">{suggestion.keyword}</span>
          <span className="inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
            {highPct}% HIGH
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-0.5">
          Appeared in {suggestion.frequency} reports across {suggestion.cluster_count} cluster{suggestion.cluster_count !== 1 ? 's' : ''}
        </p>
        {suggestion.top_counties.length > 0 && (
          <p className="text-xs text-slate-400 mt-0.5">
            Counties: {suggestion.top_counties.map(c => c.county).join(', ')}
          </p>
        )}
      </div>
      <span className="text-xs font-mono text-slate-400 whitespace-nowrap">
        {suggestion.frequency}x
      </span>
    </li>
  );
}

export function LexiconSuggestionsWidget() {
  const refetchInterval = useRefetchInterval();
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'lexicon-suggestions'],
    queryFn: () => analyticsApi.getLexiconSuggestions(),
    refetchInterval,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return <div className="animate-pulse h-24 rounded-xl bg-slate-100" />;
  }

  const suggestions = data?.suggestions ?? [];
  if (!suggestions.length) {
    return (
      <div className="text-sm text-slate-500">
        No new keyword suggestions. The lexicon covers all detected patterns.
      </div>
    );
  }

  return (
    <div>
      <p className="text-sm font-semibold text-slate-700 mb-2">
        {suggestions.length} suggested keyword{suggestions.length !== 1 ? 's' : ''}
      </p>
      <ul className="max-h-64 overflow-y-auto">
        {suggestions.map((s) => (
          <SuggestionRow key={s.keyword} suggestion={s} />
        ))}
      </ul>
    </div>
  );
}
