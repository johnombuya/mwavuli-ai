'use client';

export default function IntegratePage() {
  const backendUrl = (process.env.NEXT_PUBLIC_BACKEND_URL || '').replace(/\/$/, '');
  const docsUrl = backendUrl ? `${backendUrl}/docs` : '/docs';
  const cardClass = 'bg-white rounded-xl border border-slate-200/60 shadow-sm p-6';

  return (
    <div className="p-6 md:p-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">
          Integrate with Mwavuli
        </h1>
        <p className="text-slate-600 mb-8">
          Use the verification API in your apps, bots, and workflows. Same engine powers the public verify tool and the dashboard.
        </p>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-3">Use cases</h2>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            <li><strong>WhatsApp bot</strong> — Use n8n or Twilio to send incoming messages to <code className="bg-slate-200 px-1 rounded">POST /api/v1/verify/text</code> and reply with risk level and translated messages.</li>
            <li><strong>Web form</strong> — Add a “Verify before submit” step that checks user-entered text and shows the result (risk + explanation).</li>
            <li><strong>Ingestion</strong> — Run the ingestion pipeline (RSS + allowlisted scraping) to continuously verify content and store reports; use the same API for analytics.</li>
            <li><strong>Moderator tools</strong> — Build dashboards or tools that call the analytics and export endpoints (summary, risk distribution, report pack).</li>
          </ul>
        </section>

        <section className={`${cardClass} mb-6`}>
          <h2 className="text-xl font-semibold text-slate-900 mb-3">API docs</h2>
          <p className="text-gray-700 mb-2">
            Full request/response details and try-it-out:
          </p>
          <a
            href={docsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
          >
            OpenAPI docs (Swagger)
          </a>
          <p className="text-sm text-slate-500 mt-2">
            Set <code className="bg-slate-200 px-1 rounded">NEXT_PUBLIC_BACKEND_URL</code> (e.g. http://localhost:8000) so this link opens the backend docs. Backend must be running.
          </p>
        </section>

        <section className={cardClass}>
          <h2 className="text-xl font-semibold text-slate-900 mb-3">Key endpoints</h2>
          <ul className="space-y-2 text-gray-700 font-mono text-sm">
            <li>POST /api/v1/verify/text — Verify text (body: text, sender_id, county?)</li>
            <li>POST /api/v1/verify/media — Verify media URL (placeholder)</li>
            <li>GET /api/v1/analytics/summary — Summary stats (optional start_date, end_date)</li>
            <li>GET /api/v1/analytics/recent — Recent reports (optional status filter)</li>
            <li>GET /api/v1/export/report-pack — ZIP of reports + summary</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
