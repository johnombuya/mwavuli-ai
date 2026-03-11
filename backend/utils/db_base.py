"""
Abstract base class for Mwavuli database providers.

Both FirebaseRepository and SupabaseRepository implement this interface,
allowing the application to switch between storage backends via the
DB_PROVIDER environment variable.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class ReportRepository(ABC):
    """Provider-agnostic interface for all Mwavuli database operations."""

    # ── Reports CRUD ─────────────────────────────────────────────────

    @abstractmethod
    def save_report(self, data: dict) -> Optional[str]:
        """Enrich, deduplicate, and persist a report. Returns the report ID or None."""
        ...

    @abstractmethod
    def get_report(self, report_id: str) -> Optional[dict]:
        """Retrieve a single report by ID."""
        ...

    @abstractmethod
    def get_recent_reports(self, limit: int = 10, status: Optional[str] = None) -> list:
        """Return the most recent reports, optionally filtered by status."""
        ...

    @abstractmethod
    def update_report_status(self, report_id: str, new_status: str) -> bool:
        """Update a report's moderation status. Returns True on success."""
        ...

    @abstractmethod
    def delete_report(self, report_id: str) -> bool:
        """Delete a single report by ID. Returns True on success."""
        ...

    @abstractmethod
    def delete_reports_before(
        self, cutoff: datetime, dry_run: bool = False, batch_size: int = 500,
    ) -> int:
        """Delete reports older than *cutoff*. Returns the count of deleted docs."""
        ...

    # ── Deduplication / Coordination ─────────────────────────────────

    @abstractmethod
    def report_exists_by_content_hash(self, content_hash: str) -> bool:
        ...

    @abstractmethod
    def report_exists_by_source_url(self, source_url: str) -> bool:
        ...

    @abstractmethod
    def detect_coordinated_activity(
        self, sender_hash: str, window_minutes: int = 60, threshold: int = 10,
    ) -> bool:
        """Return True if *sender_hash* has >= *threshold* reports in the last *window_minutes*."""
        ...

    # ── Aggregates ───────────────────────────────────────────────────

    @abstractmethod
    def get_aggregate_docs(
        self,
        start_date: datetime,
        end_date: datetime,
        sector: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[dict]:
        """Return daily aggregate documents for the given date range."""
        ...

    @abstractmethod
    def save_aggregate(self, doc_id: str, data: dict) -> None:
        """Overwrite (set) an aggregate document by its deterministic ID."""
        ...

    # ── Raw-report queries ───────────────────────────────────────────

    @abstractmethod
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
        """
        Query raw reports with optional filters.

        Each returned dict must include an ``"id"`` key with the report ID.
        """
        ...

    # ── Audit logs ───────────────────────────────────────────────────

    @abstractmethod
    def write_audit_log(self, entry: dict) -> Optional[str]:
        """Append an audit event. Returns the document/row ID."""
        ...

    @abstractmethod
    def get_audit_logs(self, limit: int = 50, action: Optional[str] = None) -> list:
        """Retrieve recent audit log entries."""
        ...

    # ── Appeals ──────────────────────────────────────────────────────

    @abstractmethod
    def create_appeal(self, data: dict) -> Optional[str]:
        """Create a report appeal. Returns the appeal ID."""
        ...

    @abstractmethod
    def get_appeal(self, appeal_id: str) -> Optional[dict]:
        """Retrieve a single appeal by ID."""
        ...

    @abstractmethod
    def list_appeals(
        self, status: Optional[str] = None, limit: int = 50,
        report_id: Optional[str] = None,
    ) -> list:
        """List appeals with optional filters."""
        ...

    @abstractmethod
    def resolve_appeal(self, appeal_id: str, update: dict) -> bool:
        """Update an appeal with resolution data. Returns True on success."""
        ...

    # ── Ingestion bookkeeping ────────────────────────────────────────

    @abstractmethod
    def write_ingestion_audit(self, entry: dict) -> None:
        """Append an audit record for the ingestion pipeline."""
        ...

    @abstractmethod
    def set_ingestion_last_run(self, data: dict) -> None:
        """Store the last ingestion run summary."""
        ...

    @abstractmethod
    def get_ingestion_last_run(self) -> Optional[dict]:
        """Return last ingestion run summary or None."""
        ...

    # ── Health ───────────────────────────────────────────────────────

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the database is reachable."""
        ...
