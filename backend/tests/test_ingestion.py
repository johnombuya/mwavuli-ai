"""
Unit tests for ingestion pipeline: URL normalisation, deduplication, RSS parsing, pipeline with mocks.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure backend root is on path
_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

try:
    import app.ingestion.pipeline  # noqa: E402 - needed for patch targets; skip pipeline tests if import fails
    _pipeline_available = True
except Exception:
    _pipeline_available = False


class TestNormaliseUrl(unittest.TestCase):
    def test_strip_fragment(self):
        from app.ingestion.utils import normalise_url
        self.assertEqual(normalise_url("https://example.com/path#section"), "https://example.com/path")

    def test_strip_utm_params(self):
        from app.ingestion.utils import normalise_url
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&foo=bar"
        out = normalise_url(url)
        self.assertIn("foo=bar", out)
        self.assertNotIn("utm_source", out)
        self.assertNotIn("utm_medium", out)

    def test_empty(self):
        from app.ingestion.utils import normalise_url
        self.assertEqual(normalise_url(""), "")
        self.assertEqual(normalise_url("   "), "")


@unittest.skipUnless(_pipeline_available, "app.ingestion.pipeline not importable (missing deps)")
class TestDeduplication(unittest.TestCase):
    """Test that pipeline skips when report_exists_by_source_url returns True."""

    def test_duplicate_skipped(self):
        with patch("app.ingestion.pipeline.fetch_feeds", return_value=[
            {"url": "https://example.com/1", "title": "T", "snippet": "S", "source_type": "rss"}
        ]), \
             patch("app.ingestion.pipeline.report_exists_by_source_url", return_value=True), \
             patch("app.ingestion.pipeline.report_exists_by_content_hash", return_value=False), \
             patch("app.ingestion.pipeline.write_ingestion_audit"), \
             patch("app.ingestion.pipeline.config.is_ingestion_enabled", return_value=True), \
             patch("app.ingestion.pipeline.config.get_job_id", return_value="job1"), \
             patch("app.ingestion.pipeline.config.get_rss_feeds", return_value=["http://feed.example.com"]), \
             patch("app.ingestion.pipeline.config.get_scrape_domains", return_value=[]), \
             patch("app.ingestion.pipeline.config.get_scrape_seed_urls", return_value=[]), \
             patch("app.ingestion.pipeline.config.get_election_keywords", return_value=[]), \
             patch("app.ingestion.pipeline.config.get_user_agent", return_value="Test"), \
             patch("app.ingestion.pipeline.config.get_rate_limit_req_per_min", return_value=30):
            import asyncio
            from app.ingestion.pipeline import run_pipeline
            counts = asyncio.run(run_pipeline())
        self.assertEqual(counts["fetched"], 1)
        self.assertEqual(counts["duplicate_skipped"], 1)
        self.assertEqual(counts["saved"], 0)


class TestRssParsing(unittest.TestCase):
    """Test RSS parsing with a static fixture (no network)."""

    def test_feedparser_parses_minimal_rss(self):
        try:
            import feedparser
        except ImportError:
            self.skipTest("feedparser not installed")
        # Minimal valid RSS 2.0
        rss = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
        <title>Test</title>
        <item><title>Item 1</title><link>https://example.com/1</link><description>Desc</description></item>
        </channel></rss>"""
        parsed = feedparser.parse(rss)
        self.assertFalse(getattr(parsed, "bozo", True))
        self.assertEqual(len(parsed.entries), 1)
        self.assertEqual(parsed.entries[0].link, "https://example.com/1")
        self.assertEqual(parsed.entries[0].title, "Item 1")


@unittest.skipUnless(_pipeline_available, "app.ingestion.pipeline not importable (missing deps)")
class TestPipelineMocks(unittest.TestCase):
    """Pipeline run with mocked fetcher and analyzer; no real HTTP or Firestore."""

    @patch("app.ingestion.pipeline.get_analyzer")
    @patch("app.ingestion.pipeline.fetch_feeds", return_value=[
        {"url": "https://example.com/a", "title": "Title", "snippet": "Snippet text", "source_type": "rss"}
    ])
    @patch("app.ingestion.pipeline.config.get_rate_limit_req_per_min", return_value=30)
    @patch("app.ingestion.pipeline.config.get_user_agent", return_value="Test")
    @patch("app.ingestion.pipeline.config.get_election_keywords", return_value=[])
    @patch("app.ingestion.pipeline.config.get_scrape_seed_urls", return_value=[])
    @patch("app.ingestion.pipeline.config.get_scrape_domains", return_value=[])
    @patch("app.ingestion.pipeline.config.get_rss_feeds", return_value=[])
    @patch("app.ingestion.pipeline.config.get_job_id", return_value="test-job")
    @patch("app.ingestion.pipeline.config.is_ingestion_enabled", return_value=True)
    @patch("app.ingestion.pipeline.report_exists_by_content_hash", return_value=False)
    @patch("app.ingestion.pipeline.report_exists_by_source_url", return_value=False)
    @patch("app.ingestion.pipeline.write_ingestion_audit")
    @patch("app.ingestion.pipeline.save_report", return_value="doc-id-123")
    def test_pipeline_verify_and_save(self, save_report, write_ingestion_audit, report_exists_by_source_url,
                                     report_exists_by_content_hash, is_ingestion_enabled, get_job_id,
                                     get_rss_feeds, get_scrape_domains, get_scrape_seed_urls,
                                     get_election_keywords, get_user_agent, get_rate_limit_req_per_min,
                                     fetch_feeds, get_analyzer):
        analyzer = MagicMock()
        analyzer.analyze = AsyncMock(return_value=MagicMock(
            risk_level="MEDIUM",
            scores={"toxicity": 0.5},
            matched_keyword=None,
            gemini_context_flag=False,
        ))
        get_analyzer.return_value = analyzer

        import asyncio
        from app.ingestion.pipeline import run_pipeline
        counts = asyncio.run(run_pipeline())

        self.assertEqual(counts["fetched"], 1)
        self.assertEqual(counts["saved"], 1)
        self.assertEqual(counts["verified"], 1)
        self.assertTrue(save_report.called)
        call_args = save_report.call_args[0][0]
        self.assertEqual(call_args["source_type"], "rss")
        self.assertEqual(call_args["source_url"], "https://example.com/a")
        self.assertEqual(call_args["created_by"], "system")


if __name__ == "__main__":
    unittest.main()
