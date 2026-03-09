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
          The content verification and analytics engine for national resilience.
        </p>

        <section className={`${cardClass} mb-6`}>
          <h2 className="text-xl font-semibold text-slate-900 mb-3">Detection pipeline</h2>
          <p className="text-slate-700 mb-2">
            Mwavuli combines four layers to assess text for harmful or misleading content. The pipeline supports multiple sectors (political, health, security, fraud).
          </p>
          <ol className="list-decimal list-inside space-y-2 text-slate-700">
            <li><strong>Sector-specific lexicon check</strong> — Curated keyword lists per sector (hate speech, incitement, misinformation, fraud). A high-risk match immediately raises the risk level.</li>
            <li><strong>Detoxify</strong> — A multilingual toxicity model scores the text across categories (toxicity, severe toxicity, etc.).</li>
            <li><strong>Kenyan risk classifier</strong> — A fine-tuned transformer (DistilBERT / XLM-R) trained on Kenyan political text provides an additional domain-specific risk signal.</li>
            <li><strong>Gemini / Local LLM</strong> — Google Gemini (or a local Ollama model as fallback) checks for subtle incitement and provides translations in English, Swahili, and Sheng.</li>
          </ol>
          <p className="text-slate-700 mt-3">
            The final risk level is determined by a <strong>weighted ensemble</strong> of all four signals. Each model casts a confidence vote, and the combined score determines HIGH, MEDIUM, or LOW. The explanation field shows exactly which models contributed.
          </p>
        </section>

        <section className={`${cardClass} mb-6`}>
          <h2 className="text-xl font-semibold text-slate-900 mb-3">Model details</h2>
          <ul className="space-y-3 text-slate-700 text-sm">
            <li><strong>Lexicon</strong> — Hand-curated by Kenyan domain experts. Reviewed quarterly. Covers political, health, security, and fraud sectors.</li>
            <li><strong>Detoxify</strong> — Open-source multilingual toxicity model. Trained primarily on English data; may underperform on Swahili/Sheng.</li>
            <li><strong>Kenyan classifier</strong> — Fine-tuned on Firestore reports + Kaggle hatespeech-kenya dataset. Accuracy varies with training data size.</li>
            <li><strong>Gemini / Ollama</strong> — General-purpose LLM. Context check is prompt-based; results are probabilistic, not deterministic.</li>
          </ul>
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
          <h2 className="text-xl font-semibold text-slate-900 mb-3">Bias mitigation</h2>
          <p className="text-slate-700 text-sm">
            We run automated bias tests that swap ethnic group references in identical content to detect differential treatment. The lexicon undergoes quarterly human review with multi-community representation. An appeal mechanism allows users to challenge flagged content, and resolved appeals feed back into model retraining.
          </p>
        </section>

        <section className={`${cardClass} mb-6`}>
          <h2 className="text-xl font-semibold text-slate-900 mb-3">Privacy and use</h2>
          <p className="text-slate-700">
            Verifications are logged anonymously (salted hash of sender ID) for pattern analysis. PII (phone numbers, national IDs, emails) is automatically redacted before storage. This system is designed for harm reduction, not surveillance.
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
