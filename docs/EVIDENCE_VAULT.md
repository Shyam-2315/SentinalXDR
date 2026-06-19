# Evidence Vault

Phase 15 adds digital evidence management with hash integrity and chain-of-custody tracking.

## Capabilities

- Upload evidence files through `POST /api/evidence`.
- Store file bytes on the backend filesystem with generated safe filenames.
- Store metadata, SHA-256 hashes, tags, incident links, and status in MongoDB.
- Link or unlink evidence to incidents.
- Verify stored bytes against the original SHA-256.
- Download the original filename through the API.
- Archive and restore evidence records.
- Read custody events through `GET /api/evidence/{evidence_id}/custody`.

## Storage

Default local storage root:

```env
EVIDENCE_STORAGE_ROOT=storage/evidence
EVIDENCE_MAX_UPLOAD_MB=25
```

The Docker development stack mounts `./backend/storage/evidence` into the backend container. The production stack mounts `/app/storage/evidence` to `sentinelxdr_prod_evidence_data`.

Storage paths are internal. API responses return evidence metadata but do not expose local absolute paths.

## RBAC

- `VIEWER`: list, read, download, verify, and read custody.
- `ANALYST`: viewer permissions plus upload, link, and unlink.
- `ORG_ADMIN` and `SUPER_ADMIN`: analyst permissions plus archive and restore.

All evidence APIs are organization-scoped. Cross-organization evidence and incident links return `404`.

## Chain of Custody

Custody actions are appended for:

- `uploaded`
- `viewed`
- `downloaded`
- `linked_to_incident`
- `unlinked_from_incident`
- `verified`
- `archived`
- `restored`

Custody results are returned oldest-first for a stable timeline.

## Integrity Verification

Upload calculates SHA-256 while streaming the file to disk. Verification recalculates SHA-256 from the stored file:

- Match: `verification_status=verified`.
- Mismatch or missing file: `verification_status=failed`.

Download returns `404` if the stored file is missing.

## Frontend

Open `/evidence` for the Evidence Vault. The page includes:

- Evidence table with filters.
- Upload modal.
- Detail drawer with full metadata, SHA-256, custody timeline, verify/download controls, incident link controls, and archive/restore actions.

Incident detail pages also show linked evidence.
