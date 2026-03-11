"""
Supabase/PostgreSQL implementation of ReportRepository.

Uses the supabase-py client to perform all database operations against
a Supabase project. Tables must be created first using
backend/migrations/001_initial_schema.sql.
"""

import os
import hashlib
import json as _json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from utils.db_base import ReportRepository
from utils.db_helpers import (
    enrich_report,
    build_aggregate_update,
    default_aggregate_doc,
    apply_aggregate_increment,
    _VALID_STATUSES,
)

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")


def _iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string for Supabase filters."""
    return dt.isoformat() if dt else None


def _serialize_for_insert(d: dict) -> dict:
    """Ensure all values are JSON-serializable before inserting."""
    out = {}
    for k, v in d.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, set):
            out[k] = list(v)
        else:
            out[k] = v
    return out


class SupabaseRepository(ReportRepository):

    def __init__(self) -> None:
        self._client = None
        self._initialized = False

    def _get_client(self):
        if self._initialized:
            return self._client
        try:
            from supabase import create_client

            url = os.getenv("SUPABASE_URL", "")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            if not url or not key:
                print("Warning: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
                self._initialized = True
                return None

            self._client = create_client(url, key)
            print(f"Supabase client initialized for {url}")
            self._initialized = True
            return self._client
        except Exception as e:
            print(f"Warning: Failed to initialize Supabase: {e}")
            self._initialized = True
            return None

    # ── Reports CRUD ─────────────────────────────────────────────────

    def save_report(self, data: dict) -> Optional[str]:
        client = self._get_client()
        if client is None:
            print("Database not available. Report not saved.")
            return None
        try:
            report = enrich_report(data)

            content_hash = report.get("content_hash")
            if content_hash and self.report_exists_by_content_hash(content_hash):
                print("Duplicate report detected by content_hash; skipping save.")
                return None

            source_url = data.get("source_url")
            if source_url and self.report_exists_by_source_url(source_url):
                print("Duplicate report detected by source_url; skipping save.")
                return None

            row = _serialize_for_insert(report)
            result = client.table("reports").insert(row).execute()

            if result.data:
                doc_id = result.data[0]["id"]
                print(f"Report saved with ID: {doc_id}")
                self._update_daily_aggregate(report)
                return doc_id
            return None
        except Exception as e:
            print(f"Error saving report to Supabase: {e}")
            return None

    def get_report(self, report_id: str) -> Optional[dict]:
        client = self._get_client()
        if client is None:
            return None
        try:
            result = client.table("reports").select("*").eq("id", report_id).maybe_single().execute()
            return result.data
        except Exception as e:
            print(f"Error retrieving report: {e}")
            return None

    def get_recent_reports(self, limit: int = 10, status: Optional[str] = None) -> list:
        client = self._get_client()
        if client is None:
            return []
        try:
            query = client.table("reports").select("*").order("timestamp", desc=True)
            if status:
                query = query.eq("status", status)
            query = query.limit(limit)
            result = query.execute()
            return result.data or []
        except Exception as e:
            print(f"Error retrieving recent reports: {e}")
            return []

    def update_report_status(self, report_id: str, new_status: str) -> bool:
        if new_status not in _VALID_STATUSES:
            return False
        client = self._get_client()
        if client is None:
            return False
        try:
            result = (
                client.table("reports")
                .update({"status": new_status})
                .eq("id", report_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            print(f"Error updating report status: {e}")
            return False

    def delete_report(self, report_id: str) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            client.table("reports").delete().eq("id", report_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting report: {e}")
            return False

    def delete_reports_before(
        self, cutoff: datetime, dry_run: bool = False, batch_size: int = 500,
    ) -> int:
        client = self._get_client()
        if client is None:
            return 0
        try:
            if dry_run:
                result = (
                    client.table("reports")
                    .select("id", count="exact")
                    .lt("timestamp", _iso(cutoff))
                    .execute()
                )
                count = result.count or 0
                print(f"[dry-run] Would delete {count} reports before {cutoff.isoformat()}")
                return count

            deleted = 0
            while True:
                batch = (
                    client.table("reports")
                    .select("id")
                    .lt("timestamp", _iso(cutoff))
                    .limit(batch_size)
                    .execute()
                )
                if not batch.data:
                    break
                ids = [r["id"] for r in batch.data]
                for rid in ids:
                    client.table("reports").delete().eq("id", rid).execute()
                deleted += len(ids)
            return deleted
        except Exception as e:
            print(f"Error deleting old reports: {e}")
            return 0

    # ── Deduplication / Coordination ─────────────────────────────────

    def report_exists_by_content_hash(self, content_hash: str) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            result = (
                client.table("reports")
                .select("id")
                .eq("content_hash", content_hash)
                .limit(1)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            print(f"Error checking content_hash: {e}")
            return False

    def report_exists_by_source_url(self, source_url: str) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            result = (
                client.table("reports")
                .select("id")
                .eq("source_url", source_url)
                .limit(1)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            print(f"Error checking source_url: {e}")
            return False

    def detect_coordinated_activity(
        self, sender_hash: str, window_minutes: int = 60, threshold: int = 10,
    ) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
            result = (
                client.table("reports")
                .select("id")
                .eq("sender_hash", sender_hash)
                .gte("timestamp", _iso(cutoff))
                .limit(threshold)
                .execute()
            )
            return len(result.data or []) >= threshold
        except Exception as e:
            print(f"Error in coordinated detection: {e}")
            return False

    # ── Aggregates ───────────────────────────────────────────────────

    def get_aggregate_docs(
        self,
        start_date: datetime,
        end_date: datetime,
        sector: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[dict]:
        client = self._get_client()
        if client is None:
            return []
        try:
            sector_key = sector or "political"
            org_key = org_id or "default"

            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            result = (
                client.table("report_aggregates")
                .select("*")
                .gte("date", start_str)
                .lte("date", end_str)
                .eq("sector", sector_key)
                .eq("org_id", org_key)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error getting aggregates: {e}")
            return []

    def save_aggregate(self, doc_id: str, data: dict) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            row = _serialize_for_insert(data)
            row["id"] = doc_id
            client.table("report_aggregates").upsert(row).execute()
        except Exception as e:
            print(f"Error saving aggregate: {e}")

    def _update_daily_aggregate(self, report: Dict[str, Any]) -> None:
        """Best-effort aggregate update after saving a report."""
        try:
            timestamp = report.get("timestamp")
            if not isinstance(timestamp, datetime):
                return

            date_str = timestamp.strftime("%Y-%m-%d")
            sector = report.get("sector", "political")
            org_id_val = report.get("org_id") or "default"
            doc_id = f"{date_str}-{sector}-{org_id_val}"

            client = self._get_client()
            if client is None:
                return

            existing = (
                client.table("report_aggregates")
                .select("*")
                .eq("id", doc_id)
                .maybe_single()
                .execute()
            )

            if existing.data:
                agg = existing.data
            else:
                agg = default_aggregate_doc(date_str, sector, org_id_val)

            update = build_aggregate_update(report)
            apply_aggregate_increment(agg, update)

            row = _serialize_for_insert(agg)
            row["id"] = doc_id
            client.table("report_aggregates").upsert(row).execute()
        except Exception as e:
            print(f"Error updating daily aggregate: {e}")

    # ── Raw-report queries ───────────────────────────────────────────

    def query_reports(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sector: Optional[str] = None,
        org_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        county: Optional[str] = None,
        limit: Optional[int] = None,
        order_by_timestamp: str = "desc",
    ) -> List[dict]:
        client = self._get_client()
        if client is None:
            return []
        try:
            query = client.table("reports").select("*")
            if start_date:
                query = query.gte("timestamp", _iso(start_date))
            if end_date:
                query = query.lte("timestamp", _iso(end_date))
            if sector:
                query = query.eq("sector", sector)
            if org_id:
                query = query.eq("org_id", org_id)
            if risk_level:
                query = query.eq("risk_level", risk_level)
            if county:
                query = query.eq("county", county)

            desc = order_by_timestamp != "asc"
            query = query.order("timestamp", desc=desc)

            if limit:
                query = query.limit(limit)

            result = query.execute()
            return result.data or []
        except Exception as e:
            print(f"Error querying reports: {e}")
            return []

    # ── Audit logs ───────────────────────────────────────────────────

    def write_audit_log(self, entry: dict) -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None
        try:
            last = (
                client.table("audit_logs")
                .select("id")
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            prev_id = last.data[0]["id"] if last.data else "genesis"
        except Exception:
            prev_id = "genesis"

        chain_input = str(prev_id) + _json.dumps(entry, default=str, sort_keys=True)
        entry["prev_hash"] = hashlib.sha256(chain_input.encode()).hexdigest()[:24]

        try:
            row = _serialize_for_insert(entry)
            result = client.table("audit_logs").insert(row).execute()
            if result.data:
                return result.data[0]["id"]
            return None
        except Exception as e:
            print(f"[audit] Failed to write audit event: {e}")
            return None

    def get_audit_logs(self, limit: int = 50, action: Optional[str] = None) -> list:
        client = self._get_client()
        if client is None:
            return []
        try:
            query = client.table("audit_logs").select("*").order("timestamp", desc=True)
            if action:
                query = query.eq("action", action)
            query = query.limit(limit)
            result = query.execute()
            logs = result.data or []
            for log in logs:
                if "timestamp" in log and isinstance(log["timestamp"], str):
                    pass  # already a string from Supabase
                log.setdefault("id", log.get("id", ""))
            return logs
        except Exception as e:
            print(f"Error getting audit logs: {e}")
            return []

    # ── Appeals ──────────────────────────────────────────────────────

    def create_appeal(self, data: dict) -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None
        try:
            row = _serialize_for_insert(data)
            result = client.table("report_appeals").insert(row).execute()
            if result.data:
                return result.data[0]["id"]
            return None
        except Exception as e:
            print(f"Error creating appeal: {e}")
            return None

    def get_appeal(self, appeal_id: str) -> Optional[dict]:
        client = self._get_client()
        if client is None:
            return None
        try:
            result = (
                client.table("report_appeals")
                .select("*")
                .eq("id", appeal_id)
                .maybe_single()
                .execute()
            )
            return result.data
        except Exception as e:
            print(f"Error getting appeal: {e}")
            return None

    def list_appeals(
        self, status: Optional[str] = None, limit: int = 50,
        report_id: Optional[str] = None,
    ) -> list:
        client = self._get_client()
        if client is None:
            return []
        try:
            query = client.table("report_appeals").select("*").order("timestamp", desc=True)
            if status:
                query = query.eq("status", status)
            if report_id:
                query = query.eq("report_id", report_id)
            query = query.limit(limit)
            result = query.execute()
            appeals = result.data or []
            for a in appeals:
                a["appeal_id"] = a.get("id", "")
            return appeals
        except Exception as e:
            print(f"Error listing appeals: {e}")
            return []

    def resolve_appeal(self, appeal_id: str, update: dict) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            row = _serialize_for_insert(update)
            result = (
                client.table("report_appeals")
                .update(row)
                .eq("id", appeal_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            print(f"Error resolving appeal: {e}")
            return False

    # ── Ingestion bookkeeping ────────────────────────────────────────

    def write_ingestion_audit(self, entry: dict) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            row = _serialize_for_insert(entry)
            client.table("ingestion_audit").insert(row).execute()
        except Exception as e:
            print(f"Error writing ingestion audit: {e}")

    def set_ingestion_last_run(self, data: dict) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            row = _serialize_for_insert(data)
            row["id"] = "last_run"
            client.table("ingestion_status").upsert(row).execute()
        except Exception as e:
            print(f"Error writing ingestion status: {e}")

    def get_ingestion_last_run(self) -> Optional[dict]:
        client = self._get_client()
        if client is None:
            return None
        try:
            result = (
                client.table("ingestion_status")
                .select("*")
                .eq("id", "last_run")
                .maybe_single()
                .execute()
            )
            return result.data
        except Exception as e:
            print(f"Error reading ingestion status: {e}")
            return None

    # ── Health ───────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        return self._get_client() is not None
