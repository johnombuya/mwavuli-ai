# Firestore indexes for Mwavuli

## Ingestion deduplication

The ingestion pipeline queries the `reports` collection by:

- `source_url` (equality) — used by `report_exists_by_source_url()`
- `content_hash` (equality) — used by `report_exists_by_content_hash()`

Firestore allows **single-field equality** queries without a composite index. No extra index is required for these queries.

If you add **compound** or **range** queries (e.g. order by `timestamp` and filter by `source_url`), create the required composite index in the [Firebase Console](https://console.firebase.google.com) under Firestore → Indexes, or define them in `firestore.indexes.json` and deploy with:

```bash
firebase deploy --only firestore:indexes
```

Example `firestore.indexes.json` (if needed later):

```json
{
  "indexes": [],
  "fieldOverrides": []
}
```

Leave `indexes` empty until you add a query that requires a composite index.
