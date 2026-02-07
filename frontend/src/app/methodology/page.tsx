'use client';

import Link from 'next/link';

const cardClass = 'bg-white rounded-xl border border-slate-200/60 shadow-sm p-6';

export default function MethodologyPage() {
  return (
    <div className="p-6 md:p-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">
          How Mwavuli works
        </h1>
        <p className="text-slate-600 mb-8">
          The content verification and analytics engine for safer Kenyan elections.
        </p>

        <section className={`${cardClass} mb-6`}>
          <h2 className="text-xl font-semibold text-slate-900 mb-3">Detection pipeline</h2>
          <p className="text-slate-700 mb-2">
            Mwavuli combines three layers to assess text for harmful or misleading content in the Kenyan political context:
          </p>
          <ol className="list-decimal list-inside space-y-2 text-slate-700">
            <li><strong>Lexicon check</strong> — A curated list of high- and medium-risk keywords (hate speech, incitement, and local political terms) is matched first. Any match can immediately raise the risk level.</li>
            <li><strong>Detoxify</strong> — A multilingual toxicity model scores the text across categories (e.g. toxicity, severe toxicity). High scores contribute to the overall risk level.</li>
            <li><strong>Gemini</strong> — Google’s Gemini model is used for Kenyan-context analysis: it looks for subtle incitement or hate that may not be caught by keywords or toxicity alone. It also generates messages in English, Swahili, and Sheng.</li>
          </ol>
          <p className="text-slate-700 mt-3">
            The final risk level (HIGH, MEDIUM, LOW) is determined by combining these signals. When you see a result, the &quot;Why&quot; explanation summarizes which of these contributed.
          </p>
        </section>

        <section className={`${cardClass} mb-6`}>
          <h2 className="text-xl font-semibold text-slate-900 mb-3">Risk levels</h2>
          <ul className="space-y-3 text-slate-700">
            <li>
              <span className="font-semibold text-red-700">HIGH</span> — The content is likely to contain hate speech, incitement, or serious misinformation. We strongly recommend not sharing and verifying through official sources (e.g. IEBC).
            </li>
            <li>
              <span className="font-semibold text-amber-700">MEDIUM</span> — The content may be misleading or inflammatory. We recommend verifying with official or trusted sources before sharing.
            </li>
            <li>
              <span className="font-semibold text-green-700">LOW</span> — The content appears safe, but we still encourage verifying important claims from official sources.
            </li>
          </ul>
        </section>

        <section className={`${cardClass} mb-6`}>
          <h2 className="text-xl font-semibold text-slate-900 mb-3">Privacy and use</h2>
          <p className="text-slate-700">
            Verifications are logged anonymously (e.g. a hash of the sender ID) for pattern analysis and improving the system. We do not store identifiable personal data. The public &quot;Verify before you share&quot; tool is intended for civic use and election peacebuilding.
          </p>
        </section>

        <div className="pt-4">
          <Link href="/verify" className="text-primary-600 hover:text-primary-700 font-medium transition-colors">
            Try Verify before you share →
          </Link>
        </div>
      </div>
    </div>
  );
}
