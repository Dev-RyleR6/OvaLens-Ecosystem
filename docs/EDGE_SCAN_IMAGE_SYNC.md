# Saved scan image synchronization

Task: **TASK-NEW-EDGE-IMAGE-SYNC-01**.

The Edge station saves the exact stationary inference snapshot as a JPEG before
committing its scan. Three-board automatic capture already did this; manual
diagnostics and paired dual-board captures now save their snapshot too. Preview
and simulation remain unrecorded. Legacy metadata-only callers and historical
records without a snapshot cannot supply a photo.

SQLite WAL now stores separate metadata and photo acknowledgements. The worker
syncs metadata first and uploads at most five photos per pass. A failed upload
retains the JPEG and persistent error/attempt state; retries continue after
restart. Least-recently-attempted ordering prevents a missing photo from blocking
later photos. The operator pending count and local history/export sync flags
include outstanding photos. Existing saved JPEGs are discovered automatically,
even when their classification metadata was already acknowledged.

The authenticated upload API verifies JPEG contents, a 10 MiB default byte limit
and 25-megapixel pixel limit, writes through an atomic temporary file, and returns
the scan UUID, canonical media URL, SHA-256 digest and original byte count. Edge
requires all acknowledgement fields before clearing a photo. A PostgreSQL scan
row lock serializes uploads for the same UUID; identical replay is successful,
and different bytes receive HTTP 409 to preserve evidence. Metadata replay cannot
erase a photo URL. Disk failures return a retryable HTTP 503 without committing a
photo URL. Both local and backend original JPEGs remain on disk after sync.

Backend `STORAGE_DIR` holds photos and `/storage/<uuid>.jpg` serves them. Vite and
Nginx proxy `/storage` so Scan Explorer's existing image display can load photos.
Docker persists the photo directory in the `scan_images` volume independently of
PostgreSQL. Backups must include both. No application services or hardware were
started, reset, or moved during implementation; API tests use isolated temporary
photo directories and their own UUID records.

Restart the backend, Edge app and dashboard dev server to load the change. Normal
scan operation saves and syncs photos automatically when the configured backend
and API key are available. Offline operation continues locally. Existing saved
photos upload after restart; old scans without photos remain metadata-only.

Verification on 2026-10-09: the required repository gate passed all 27 backend
API tests and all 394 Edge tests, with no skips; dashboard TypeScript and production
build passed. `docker compose config --quiet` passed. Targeted tests cover lost
acknowledgements, migration/backfill, mismatched acknowledgements, missing files,
fairness, storage failure, conflicts and exact-byte retrieval from the actual
backend API with PostgreSQL. Existing FastAPI TestClient and Vite/plugin
deprecation warnings remain; they did not prevent verification.
