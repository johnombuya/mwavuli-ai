'use client';

import { useState, useRef, useCallback } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { verifyApi, type VerifyResponse } from '@/lib/api';

const RISK_COLORS: Record<string, string> = {
  HIGH: 'bg-red-50 border-red-300 text-red-800',
  MEDIUM: 'bg-amber-50 border-amber-300 text-amber-800',
  LOW: 'bg-green-50 border-green-300 text-green-800',
};

const cardClass = 'bg-white rounded-xl border border-slate-200/60 shadow-sm p-6';

type Mode = 'text' | 'image' | 'audio' | 'video';

const MODE_LABELS: Record<Mode, string> = {
  text: 'Text',
  image: 'Image',
  audio: 'Audio',
  video: 'Video',
};

const ACCEPT_MAP: Record<string, string> = {
  image: 'image/jpeg,image/png,image/webp,image/gif',
  audio: 'audio/*',
  video: 'video/*',
};

const MAX_SIZE_MB: Record<string, number> = {
  image: 5,
  audio: 50,
  video: 50,
};

export default function VerifyPage() {
  const { t } = useLanguage();
  const [mode, setMode] = useState<Mode>('text');
  const [text, setText] = useState('');
  const [mediaUrl, setMediaUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [county, setCounty] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isMediaMode = mode !== 'text';

  const resetMedia = useCallback(() => {
    setFile(null);
    setMediaUrl('');
  }, []);

  function switchMode(m: Mode) {
    setMode(m);
    setResult(null);
    setError(null);
    resetMedia();
    setText('');
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) validateAndSetFile(dropped);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }

  function validateAndSetFile(f: File) {
    const maxBytes = (MAX_SIZE_MB[mode] || 50) * 1024 * 1024;
    if (f.size > maxBytes) {
      setError(`File too large (${(f.size / 1024 / 1024).toFixed(1)} MB). Max ${MAX_SIZE_MB[mode] || 50} MB.`);
      return;
    }
    setError(null);
    setFile(f);
    setMediaUrl('');
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);

    if (mode === 'text') {
      const trimmed = text.trim();
      if (!trimmed) { setError('Please enter some text to verify.'); return; }
      if (trimmed.length > 5000) { setError('Text is too long (max 5000 characters).'); return; }
    } else if (!file && !mediaUrl.trim()) {
      setError(`Please upload a ${mode} file or enter a URL.`);
      return;
    }

    setLoading(true);
    try {
      if (mode === 'text') {
        const res = await verifyApi.verifyText({
          text: text.trim(),
          sender_id: 'public-verify',
          county: county.trim() || undefined,
        });
        setResult(res);
      } else if (file) {
        const res = await verifyApi.verifyMediaUpload(file, 'public-verify', county.trim() || undefined);
        setResult(res);
      } else {
        const res = await verifyApi.verifyMedia({
          media_url: mediaUrl.trim(),
          media_type: mode,
          sender_id: 'public-verify',
          county: county.trim() || undefined,
        });
        setResult(res);
      }
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
          Check text, images, audio, or video for harmful or misleading content.
          Results include messages in English, Swahili, and Sheng.
        </p>

        {/* Mode tabs */}
        <div className="flex gap-1 p-1 bg-slate-100 rounded-lg mb-6 w-fit">
          {(['text', 'image', 'audio', 'video'] as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => switchMode(m)}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                mode === m
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {MODE_LABELS[m]}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'text' ? (
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
          ) : (
            <div className="space-y-3">
              {/* Drop zone */}
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
                className={`relative cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
                  dragActive
                    ? 'border-primary-400 bg-primary-50'
                    : file
                    ? 'border-green-400 bg-green-50'
                    : 'border-slate-300 bg-slate-50 hover:border-primary-300 hover:bg-primary-50/50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPT_MAP[mode]}
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) validateAndSetFile(f);
                  }}
                  disabled={loading}
                />
                {file ? (
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-green-800">
                      {file.name}
                    </p>
                    <p className="text-xs text-green-600">
                      {(file.size / 1024 / 1024).toFixed(2)} MB &middot;{' '}
                      <button
                        type="button"
                        className="underline hover:text-red-600"
                        onClick={(e) => {
                          e.stopPropagation();
                          setFile(null);
                        }}
                      >
                        Remove
                      </button>
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="text-3xl text-slate-400">
                      {mode === 'image' ? '🖼️' : mode === 'audio' ? '🎵' : '🎬'}
                    </div>
                    <p className="text-sm text-slate-600">
                      Drag and drop a {mode} file here, or click to browse
                    </p>
                    <p className="text-xs text-slate-400">
                      Max {MAX_SIZE_MB[mode]} MB
                    </p>
                  </div>
                )}
              </div>

              {/* URL fallback */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-white px-2 text-slate-400">or paste a URL</span>
                </div>
              </div>
              <input
                type="url"
                className="w-full rounded-lg border border-slate-300 p-3 text-slate-900 placeholder-slate-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
                placeholder={`https://example.com/${mode === 'image' ? 'photo.jpg' : mode === 'audio' ? 'recording.mp3' : 'clip.mp4'}`}
                value={mediaUrl}
                onChange={(e) => {
                  setMediaUrl(e.target.value);
                  if (e.target.value) setFile(null);
                }}
                disabled={loading || !!file}
              />
            </div>
          )}

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
            {loading
              ? t.verifyChecking
              : mode === 'text'
              ? t.verifyButton
              : `Verify ${mode}`}
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
              <div className={cardClass}>
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
