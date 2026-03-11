"""
Firebase/Firestore implementation of ReportRepository.

Wraps all existing Firestore operations (reports, aggregates, audit logs,
appeals, ingestion) into the provider-agnostic ReportRepository interface.
"""

import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore
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


class FirebaseRepository(ReportRepository):

    def __init__(self) -> None:
        self._db = None
        self._initialized = False

    # ── Internal helpers ─────────────────────────────────────────────

    def _get_db(self):
        if self._initialized:
            return self._db
        try:
            raw_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
            if not raw_path:
                raw_path = "firebase-service-account.json"
            path = Path(raw_path)
            if not path.is_absolute():
                path = (_backend_root / path).resolve()
            service_account_path = str(path)
            if not path.exists():
                fallback = _backend_root / "firebase-service-account.json"
                if fallback.exists():
                    service_account_path = str(fallback)
                else:
                    print(f"Warning: Firebase credentials file not found at {service_account_path}")
                    self._initialized = True
                    return None

            cred = credentials.Certificate(service_account_path)
            database_id = os.getenv("FIREBASE_DATABASE_ID", None)

            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(cred)

            if database_id:
                self._db = firestore.client(database_id=database_id)
                print(f"Firebase Firestore initialized successfully with database: {database_id}")
            else:
                self._db = firestore.client()
                print("Firebase Firestore initialized successfully with default database.")

            self._initialized = True
            return self._db
        except Exception as e:
            print(f"Warning: Failed to initialize Firebase: {e}")
            self._initialized = True
            return None

    def _data_root(self):
        """Return the Firestore reference to artifacts/mwavuli/public/data."""
        db = self._get_db()
        if db is None:
            return None
        return (
            db.collection("artifacts")
            .document("mwavuli")
            .collection("public")
            .document("data")
        )

    def _reports_ref(self):
        root = self._data_root()
        return root.collection("reports") if root else None

    def _aggregates_ref(self):
        root = self._data_root()
        return root.collection("report_aggregates") if root else None

    def _audit_ref(self):
        root = self._data_root()
        return root.collection("audit_logs") if root else None

    def _appeals_ref(self):
        root = self._data_root()
        return root.collection("report_appeals") if root else None

    def _ingestion_audit_ref(self):
        root = self._data_root()
        return root.collection("ingestion_audit") if root else None

    def _ingestion_status_ref(self):
        root = self._data_root()
        return root.collection("ingestion_status") if root else None

    # ── Reports CRUD ─────────────────────────────────────────────────

    def save_report(self, data: dict) -> Optional[str]:
        db = self._get_db()
        if db is None:
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

            ref = self._reports_ref()
            if ref is None:
                return None

            doc_ref = ref.add(report)
            doc_id = doc_ref[1].id
            print(f"Report saved with ID: {doc_id}")

            self._update_daily_aggregate(db, report)
            return doc_id
        except Exception as e:
            print(f"Error saving report to Firestore: {e}")
            return None

    def get_report(self, report_id: str) -> Optional[dict]:
        ref = self._reports_ref()
        if ref is None:
            return None
        try:
            doc = ref.document(report_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"Error retrieving report: {e}")
            return None

    def get_recent_reports(self, limit: int = 10, status: Optional[str] = None) -> list:
        ref = self._reports_ref()
        if ref is None:
            return []
        try:
            fetch_limit = limit * 4 if status else limit
            query = ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(fetch_limit)
            reports = []
            for doc in query.stream():
                report = doc.to_dict()
                if status and report.get("status") != status:
                    continue
                report["id"] = doc.id
                reports.append(report)
                if len(reports) >= limit:
                    break
            return reports
        except Exception as e:
            print(f"Error retrieving recent reports: {e}")
            return []

    def update_report_status(self, report_id: str, new_status: str) -> bool:
        if new_status not in _VALID_STATUSES:
            return False
        ref = self._reports_ref()
        if ref is None:
            return False
        try:
            doc_ref = ref.document(report_id)
            doc = doc_ref.get()
            if not doc.exists:
                return False
            doc_ref.update({"status": new_status})
            return True
        except Exception as e:
            print(f"Error updating report status: {e}")
            return False

    def delete_report(self, report_id: str) -> bool:
        ref = self._reports_ref()
        if ref is None:
            return False
        try:
            ref.document(report_id).delete()
            return True
        except Exception as e:
            print(f"Error deleting report: {e}")
            return False

    def delete_reports_before(
        self, cutoff: datetime, dry_run: bool = False, batch_size: int = 500,
    ) -> int:
        ref = self._reports_ref()
        if ref is None:
            return 0
        query = ref.where("timestamp", "<", cutoff).limit(batch_size)
        deleted = 0
        while True:
            docs = list(query.stream())
            if not docs:
                break
            for doc in docs:
                if dry_run:
                    ts = doc.to_dict().get("timestamp", "?")
                    print(f"[dry-run] Would delete {doc.id} (timestamp={ts})")
                else:
                    doc.reference.delete()
                deleted += 1
        return deleted

    # ── Deduplication / Coordination ─────────────────────────────────

    def report_exists_by_content_hash(self, content_hash: str) -> bool:
        ref = self._reports_ref()
        if ref is None:
            return False
        try:
            query = ref.where("content_hash", "==", content_hash).limit(1)
            return len(list(query.stream())) > 0
        except Exception as e:
            print(f"Error checking content_hash in Firestore: {e}")
            return False

    def report_exists_by_source_url(self, source_url: str) -> bool:
        ref = self._reports_ref()
        if ref is None:
            return False
        try:
            query = ref.where("source_url", "==", source_url).limit(1)
            return len(list(query.stream())) > 0
        except Exception as e:
            print(f"Error checking source_url in Firestore: {e}")
            return False

    def detect_coordinated_activity(
        self, sender_hash: str, window_minutes: int = 60, threshold: int = 10,
    ) -> bool:
        ref = self._reports_ref()
        if ref is None:
            return False
        try:
            cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
            query = (
                ref.where("sender_hash", "==", sender_hash)
                .where("timestamp", ">=", cutoff)
                .limit(threshold)
            )
            return len(list(query.stream())) >= threshold
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
        coll = self._aggregates_ref()
        if coll is None:
            return []

        sector_key = sector or "political"
        org_key = org_id or "default"

        cursor = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_norm = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

        results: List[dict] = []
        while cursor <= end_norm:
            date_str = cursor.strftime("%Y-%m-%d")
            doc_id = f"{date_str}-{sector_key}-{org_key}"
            doc = coll.document(doc_id).get()
            if doc.exists:
                results.append(doc.to_dict() or {})
            cursor += timedelta(days=1)
        return results

    def save_aggregate(self, doc_id: str, data: dict) -> None:
        coll = self._aggregates_ref()
        if coll is None:
            return
        try:
            coll.document(doc_id).set(data)
        except Exception as e:
            print(f"Error saving aggregate: {e}")

    def _update_daily_aggregate(self, db, report: Dict[str, Any]) -> None:
        """Transactional best-effort aggregate update after saving a report."""
        try:
            coll = self._aggregates_ref()
            if coll is None:
                return

            timestamp = report.get("timestamp")
            if not isinstance(timestamp, datetime):
                return

            date_str = timestamp.strftime("%Y-%m-%d")
            sector = report.get("sector", "political")
            org_id_val = report.get("org_id") or "default"

            doc_id = f"{date_str}-{sector}-{org_id_val}"
            doc_ref = coll.document(doc_id)

            update = build_aggregate_update(report)

            transaction = db.transaction()

            def _txn(transaction, ref):
                snapshot = ref.get(transaction=transaction)
                if snapshot.exists:
                    agg = snapshot.to_dict() or {}
                else:
                    agg = default_aggregate_doc(date_str, sector, org_id_val)

                apply_aggregate_increment(agg, update)
                transaction.set(ref, agg)

            _txn(transaction, doc_ref)
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
        ref = self._reports_ref()
        if ref is None:
            return []
        try:
            query = ref
            if start_date:
                query = query.where("timestamp", ">=", start_date)
            if end_date:
                query = query.where("timestamp", "<=", end_date)
            if sector:
                query = query.where("sector", "==", sector)
            if org_id:
                query = query.where("org_id", "==", org_id)
            if risk_level:
                query = query.where("risk_level", "==", risk_level)
            if county:
                query = query.where("county", "==", county)

            direction = (
                firestore.Query.ASCENDING
                if order_by_timestamp == "asc"
                else firestore.Query.DESCENDING
            )
            query = query.order_by("timestamp", direction=direction)

            if limit:
                query = query.limit(limit)

            results = []
            for doc in query.stream():
                d = doc.to_dict()
                d["id"] = doc.id
                results.append(d)
            return results
        except Exception as e:
            print(f"Error querying reports: {e}")
            return []

    # ── Audit logs ───────────────────────────────────────────────────

    def write_audit_log(self, entry: dict) -> Optional[str]:
        ref = self._audit_ref()
        if ref is None:
            return None
        try:
            import json as _json
            last_doc = list(ref.order_by("timestamp", direction="DESCENDING").limit(1).stream())
            prev_id = last_doc[0].id if last_doc else "genesis"
        except Exception:
            prev_id = "genesis"

        import json as _json
        chain_input = prev_id + _json.dumps(entry, default=str, sort_keys=True)
        entry["prev_hash"] = hashlib.sha256(chain_input.encode()).hexdigest()[:24]

        try:
            _, doc_ref = ref.add(entry)
            return doc_ref.id
        except Exception as e:
            print(f"[audit] Failed to write audit event: {e}")
            return None

    def get_audit_logs(self, limit: int = 50, action: Optional[str] = None) -> list:
        ref = self._audit_ref()
        if ref is None:
            return []
        try:
            query = ref.order_by("timestamp", direction="DESCENDING")
            if action:
                query = query.where("action", "==", action)
            query = query.limit(limit)
            logs = []
            for doc in query.stream():
                d = doc.to_dict()
                d["id"] = doc.id
                if "timestamp" in d and hasattr(d["timestamp"], "isoformat"):
                    d["timestamp"] = d["timestamp"].isoformat()
                logs.append(d)
            return logs
        except Exception as e:
            print(f"Error getting audit logs: {e}")
            return []

    # ── Appeals ──────────────────────────────────────────────────────

    def create_appeal(self, data: dict) -> Optional[str]:
        ref = self._appeals_ref()
        if ref is None:
            return None
        try:
            _, doc_ref = ref.add(data)
            return doc_ref.id
        except Exception as e:
            print(f"Error creating appeal: {e}")
            return None

    def get_appeal(self, appeal_id: str) -> Optional[dict]:
        ref = self._appeals_ref()
        if ref is None:
            return None
        try:
            doc = ref.document(appeal_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"Error getting appeal: {e}")
            return None

    def list_appeals(
        self, status: Optional[str] = None, limit: int = 50,
        report_id: Optional[str] = None,
    ) -> list:
        ref = self._appeals_ref()
        if ref is None:
            return []
        try:
            query = ref.order_by("timestamp", direction="DESCENDING")
            if status:
                query = query.where("status", "==", status)
            if report_id:
                query = query.where("report_id", "==", report_id)
            query = query.limit(limit)
            appeals = []
            for doc in query.stream():
                d = doc.to_dict()
                d["appeal_id"] = doc.id
                if "timestamp" in d and hasattr(d["timestamp"], "isoformat"):
                    d["timestamp"] = d["timestamp"].isoformat()
                if "resolved_at" in d and hasattr(d["resolved_at"], "isoformat"):
                    d["resolved_at"] = d["resolved_at"].isoformat()
                appeals.append(d)
            return appeals
        except Exception as e:
            print(f"Error listing appeals: {e}")
            return []

    def resolve_appeal(self, appeal_id: str, update: dict) -> bool:
        ref = self._appeals_ref()
        if ref is None:
            return False
        try:
            doc_ref = ref.document(appeal_id)
            doc = doc_ref.get()
            if not doc.exists:
                return False
            doc_ref.update(update)
            return True
        except Exception as e:
            print(f"Error resolving appeal: {e}")
            return False

    # ── Ingestion bookkeeping ────────────────────────────────────────

    def write_ingestion_audit(self, entry: dict) -> None:
        ref = self._ingestion_audit_ref()
        if ref is None:
            return
        try:
            ref.add(entry)
        except Exception as e:
            print(f"Error writing ingestion audit: {e}")

    def set_ingestion_last_run(self, data: dict) -> None:
        ref = self._ingestion_status_ref()
        if ref is None:
            return
        try:
            ref.document("last_run").set(data)
        except Exception as e:
            print(f"Error writing ingestion status: {e}")

    def get_ingestion_last_run(self) -> Optional[dict]:
        ref = self._ingestion_status_ref()
        if ref is None:
            return None
        try:
            doc = ref.document("last_run").get()
            if doc and doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"Error reading ingestion status: {e}")
            return None

    # ── Health ───────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        return self._get_db() is not None
