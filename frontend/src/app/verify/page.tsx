'use client';

import { useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { verifyApi, type VerifyResponse } from '@/lib/api';

const RISK_COLORS: Record<string, string> = {
  HIGH: 'bg-red-50 border-red-300 text-red-800',
  MEDIUM: 'bg-amber-50 border-amber-300 text-amber-800',
  LOW: 'bg-green-50 border-green-300 text-green-800',
};

const cardClass = 'bg-white rounded-xl border border-slate-200/60 shadow-sm p-6';

export default function VerifyPage() {
  const { t } = useLanguage();
  const [text, setText] = useState('');
  const [county, setCounty] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerifyResponse | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    const trimmed = text.trim();
    if (!trimmed) {
      setError('Please enter some text to verify.');
      return;
    }
    if (trimmed.length > 5000) {
      setError('Text is too long (max 5000 characters).');
      return;
    }
    setLoading(true);
    try {
      const res = await verifyApi.verifyText({
        text: trimmed,
        sender_id: 'public-verify',
        county: county.trim() || undefined,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 md:p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">
          Verify before you share
        </h1>
        <p className="text-slate-600 mb-6">
          Paste text to check for harmful or misleading content. Results include messages in English, Swahili, and Sheng.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="text" className="block text-sm font-medium text-slate-700 mb-1">
              {t.textToVerify}
            </label>
            <textarea
              id="text"
              rows={5}
              className="w-full rounded-lg border border-slate-300 p-3 text-slate-900 placeholder-slate-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="Paste the message or claim you want to check..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={5001}
              disabled={loading}
            />
            <p className="mt-1 text-xs text-slate-500">{text.length} / 5000</p>
          </div>
          <div>
            <label htmlFor="county" className="block text-sm font-medium text-slate-700 mb-1">
              {t.countyOptional}
            </label>
            <input
              id="county"
              type="text"
              className="w-full rounded-lg border border-slate-300 p-2 text-slate-900 placeholder-slate-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="e.g. Nairobi"
              value={county}
              onChange={(e) => setCounty(e.target.value)}
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-primary-600 px-4 py-3 font-medium text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? t.verifyChecking : t.verifyButton}
          </button>
        </form>

        {error && (
          <div className="mt-4 p-4 rounded-xl bg-red-50 border border-red-200 text-red-800">
            {error}
          </div>
        )}

        {result && (
          <div className="mt-6 space-y-4">
            <div className={`rounded-xl border-2 p-4 ${RISK_COLORS[result.risk_level] || 'bg-slate-50 border-slate-200 text-slate-800'}`}>
              <p className="font-semibold">{t.riskLevel}: {result.risk_level}</p>
              <p className="mt-2">{result.messages.english}</p>
            </div>
            <div className={`${cardClass} space-y-3`}>
              <p className="text-sm font-medium text-slate-700">{t.swahili}</p>
              <p className="text-slate-900">{result.messages.swahili}</p>
              <p className="text-sm font-medium text-slate-700 pt-2">{t.sheng}</p>
              <p className="text-slate-900">{result.messages.sheng}</p>
            </div>
            <div className="rounded-xl border border-primary-200 bg-primary-50 p-4">
              <p className="text-sm font-medium text-primary-700">{t.prebunkingTip}</p>
              <p className="text-primary-900 mt-1">{result.prebunking_tip}</p>
            </div>
            {result.explanation && (
              <div className={`${cardClass}`}>
                <p className="text-sm font-medium text-slate-700">{t.explanation}</p>
                <p className="text-slate-900 mt-1">{result.explanation}</p>
              </div>
            )}
            {result.matched_keyword && !result.explanation && (
              <p className="text-sm text-slate-600">
                Matched keyword: <strong>{result.matched_keyword}</strong>
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
