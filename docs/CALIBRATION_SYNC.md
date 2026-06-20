# JPilot ↔ Stack Calibration Studio

JPilot syncs **skills** and **Knowledge Packs** from [Stack Calibration Studio](https://scstudio.nexxus-tech.com) and sends **calibration feedback** when a chat session fails to meet the user's objective.

**Normative HTTP contract (shared with scstudio):** [JPILOT_SCSTUDIO_INTEGRATION.md](./JPILOT_SCSTUDIO_INTEGRATION.md)

**Canonical scstudio spec:** [Nexxus-Tech-SAS/scstudio `docs/JPILOT_INTEGRATION.md`](https://github.com/Nexxus-Tech-SAS/scstudio/blob/main/docs/JPILOT_INTEGRATION.md) (Knowledge Pack section, contract v1)

---

## Overview

| Direction | Endpoint (scstudio) | JPilot client |
|-----------|-------------------|---------------|
| Blueprint catalog (read-only) | `POST /calibrations/catalog` | `fetch_calibration_catalog` + `GET /copilot/calibrations/catalog` |
| Knowledge Pack + skills sync | `POST /calibrations/sync` | `calibration_sync_service.py` + `POST /copilot/calibrations/sync` |
| Knowledge Pack download | `GET /calibrations/knowledge-packs/{packId}/{version}` | `knowledge_pack_service.process_knowledge_pack_from_sync` |
| Uninstall local skill | — | `DELETE /copilot/calibrations/{skillId}?version=` |
| Push feedback | `POST /skill-feedback` | `skill_feedback_service.py` |
| In-app export | — | `POST /copilot/calibration-feedback` (local API → forwards to scstudio) |

Custom org calibrations **persist across JPilot upgrades**: synced content is cached under `data/calibrations/` with version pins; customer overlays take precedence until the org opts into a Nexxus base update.

### Chat agent tools

| Tool | Purpose |
|------|---------|
| `list_official_blueprint_catalog` | Official Nexxus blueprint library for this license; includes `installedBlueprints` |
| `search_stack_calibration_memory` | Search memory playbooks from **installed** skills (pack-embedded + legacy) |

Install path: **Calibration Studio → Sync**, manual `.knowpkg` import, or legacy per-skill `.calpkg` sync when no Knowledge Pack is returned.

After a **license change in Nexxus Admin**, open Calibration Studio and click **Refresh entitlements** (JPilot re-syncs with Nexxus licensing, then reloads the catalog).

---

## Knowledge Pack (`.knowpkg`) — JPilot sync contract v1

**Contract version:** 1 (introduced scstudio v0.09)

Normative JPilot-side implementation of Personas, Overlays, Knowledge Assignments, and Blueprints as a **single signed, versioned bundle**.

### Design principles

| Principle | Rule |
|-----------|------|
| Source of truth (authoring) | SCStudio MongoDB |
| Source of truth (runtime) | JPilot local Knowledge Pack cache |
| Live persona API | **Not used** at chat time |
| Offline / air-gap | Manual `.knowpkg` import or pre-synced cache |
| Blueprints | Embedded in pack **or** referenced via transitional per-skill sync |

### Publication model

```
Authoring (Studio)  →  Build + sign pack  →  GridFS  →  JPilot pull/import  →  Local cache
```

Personas, overlays, and assignments are **frozen at publish time** — same as blueprint `.calpkg` artifacts.

### Extended POST /calibrations/sync

#### Request (backward compatible)

JPilot adds `installedKnowledgePack` when a pack is active locally:

```json
{
  "appFingerprint": "<installation fingerprint>",
  "appName": "JPilot",
  "installedVersions": { "nexxus-netscaler-waf-tuning": "2.1.0" },
  "installedKnowledgePack": {
    "id": "nexxus-global",
    "version": "2.3.0",
    "contentHash": "sha256:abcdef..."
  }
}
```

#### Response

```json
{
  "status": "active",
  "licenseType": "enterprise",
  "clientId": "client-acme",
  "knowledgePack": {
    "id": "nexxus-global",
    "version": "2.4.0",
    "contentHash": "sha256:...",
    "packageSignature": "<Ed25519>",
    "bundleUrl": "/calibrations/knowledge-packs/nexxus-global/2.4.0"
  },
  "stackProfile": {
    "id": "client-acme-default",
    "version": "2.4.0",
    "knowledgePackVersion": "2.4.0"
  },
  "skills": [],
  "removed": []
}
```

| Field | JPilot behavior |
|-------|-----------------|
| `knowledgePack` | Preferred delivery; absent → legacy per-skill `skills[]` only |
| `knowledgePack.bundleUrl` omitted | `contentHash` matches local → skip download (304-style) |
| `skills[]` | Transitional; still installed when pack absent or during migration |
| `stackProfile.knowledgePackVersion` | Honored as pin when version exists locally |

**JPilot client:** `sync_calibrations_from_studio` · local proxy `POST /copilot/calibrations/sync`

### Package format (`.knowpkg`)

Zip archive, Ed25519-signed root manifest (Nexxus public key: `backend-api/app/resources/keys/nexxus_calibration_signing.pub`):

```
knowpkg/
├── manifest.json
├── catalog/vendors.json
├── personas/{architect,operator,analyst}/persona.json, behavior.md, permissions.json
├── overlays/vendors|products|domains/
├── assignments/{assignmentId}.json
├── blueprints/{skillId}/   ← same layout as .calpkg
└── indexes/blueprint-index.json, assignment-index.json
```

### JPilot local storage layout

```
data/calibrations/knowledge-packs/{packId}/{version}/   ← extracted pack
data/calibrations/knowledge-packs/{packId}/current     ← symlink to active version
data/calibrations/knowledge-packs/{packId}/previous     ← rollback target
```

Install is atomic: extract to staging → verify signature + contentHash → swap `current`. Failed verify keeps the previous `current` pack.

MongoDB `knowledge_pack_state` stores active version, pin, sync schedule, and metadata.

### Calibration Studio UI (JPilot)

Implemented in **Calibration Studio** (`/calibration-studio`):

| Option | Local API |
|--------|-----------|
| Installed Knowledge Pack | `GET /copilot/knowledge-pack` |
| Sync now | `POST /copilot/calibrations/sync` |
| Sync schedule | `PUT /copilot/knowledge-pack/schedule` (default 6h; also on startup) |
| Import pack file | `POST /copilot/knowledge-pack/import` (multipart `.knowpkg`) |
| Rollback | `POST /copilot/knowledge-pack/rollback` |
| Pin version | `PUT /copilot/knowledge-pack/pin` |
| Legacy skills | Per-skill list when sync returns `skills[]` without pack or outside pack embed |

### Runtime assembly (local only)

**No SCStudio HTTP during chat.** JPilot never calls `/api/studio/personas*` or `/knowledge-assignments*` at chat time — those are authoring-only.

Assembly order when an active Knowledge Pack exists:

```
1. Platform base prompt (JPilot image, current chat role)
2. Platform gates (non-overridable)
3. personas/{role}/behavior.md + permissions.json
4. overlays: vendor → product → domain (promptDelta only)
5. assignments matching persona + vendor + device (+ domain)
6. matched blueprints (cap 2/turn): prompts/{role}.md + memory RAG
7. tools = platform ∩ persona.permissions ∩ blueprint.toolPack
```

Precedence: **Platform > Persona permissions > Persona behavior > Overlays > Blueprint content**.

**Legacy fallback:** when sync returns no `knowledgePack` or no pack is installed, runtime uses `data/calibrations/{skillId}/{version}/` and `calibration_matcher.py` unchanged.

**Implementation:** `knowledge_pack_runtime.py` · wired from `copilot_orchestrator._apply_blueprint_context`

### Security

| Control | Requirement |
|---------|-------------|
| Ed25519 signature | Verify before activating when `packageSignature` present |
| contentHash | SHA-256 of archive; compare on sync |
| Tier + client gate | Sync returns only entitled packs (scstudio) |
| Tamper rejection | Failed verify → keep previous `current` pack |

**Transition:** when `packageSignature` is empty (pre-signing pipeline), JPilot verifies `contentHash` only and logs a warning.

### Implementation checklist

- [x] Send `installedKnowledgePack` on sync
- [x] Parse `knowledgePack` in sync response
- [x] Download GET `bundleUrl` when hash differs
- [x] Verify Ed25519 + contentHash
- [x] Extract to local layout; atomic install
- [x] Calibration Studio UI options
- [x] Runtime assembly from `current` pack only
- [x] Air-gap manual import
- [x] Rollback to `previous`
- [x] Legacy fallback when `knowledgePack` absent

---

## Send to Calibration (in-app)

When the user did not achieve their goal, chat exposes **Send to Calibration**:

1. User clicks the button (or it is suggested after tool-limit / error replies).
2. Optional dialog: user goal summary, category, comment, include appliance name.
3. JPilot backend builds a redacted payload and `POST`s to `{nexxus_calibration_base_url}/skill-feedback`.
4. scstudio creates a `skill_feedback` record (`status: new`) and links it to calibration chat for Nexxus SMEs or Enterprise Pro authors.

### Local API

`POST /copilot/calibration-feedback`

See [JPILOT_SCSTUDIO_INTEGRATION.md](./JPILOT_SCSTUDIO_INTEGRATION.md) for request/response shapes.

### Frontend

- `frontend/src/services/calibrationFeedback.js`
- `frontend/src/utils/buildCalibrationFeedbackPayload.js`
- Button in `ChatPane.vue` (beta + classic layouts)

### Settings (env)

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXXUS_CALIBRATION_BASE_URL` | `https://scstudio.nexxus-tech.com` | scstudio public base URL |
| `CALIBRATION_SYNC_ENABLED` | `true` | Disable outbound sync (air-gapped installs) |
| `CALIBRATION_FEEDBACK_ENABLED` | `true` | Disable outbound feedback (air-gapped installs) |

**Local dev:** run scstudio with `docker compose up` (port 8090) and set `NEXXUS_CALIBRATION_BASE_URL=http://host.docker.internal:8090` on JPilot.

Studio LLM keys are configured **only in scstudio** (Settings → AI Providers). JPilot never sends customer LLM keys to Studio.

---

## What Studio changes vs platform code

| Layer | Calibrated in Studio | Updated via jpilot release |
|-------|----------------------|----------------------------|
| Personas, overlays, assignments, skill prompts, memory | Yes (via Knowledge Pack) | — |
| Tool pack (prefer existing MCP tools) | Yes | — |
| MCP SSH / Next-Gen execution | No | `mcp-server/` |
| Orchestrator gates, tool schemas | No (proposal only) | `backend-api/` |

See sample skill: [calibrations/samples/netscaler-firmware-ha-upgrade/](./calibrations/samples/netscaler-firmware-ha-upgrade/).

---

## Phasing

| Phase | JPilot | scstudio |
|-------|--------|----------|
| **1** | Send to Calibration, `/skill-feedback` forward | Inbox + calibration chat pre-fill |
| **2** | Pull sync, local cache, matcher injection | Publish `.calpkg`, signing |
| **3** | Knowledge Pack consumer + UI + runtime assembly | Pack builder + GridFS |
| **4** | Auto-suggest after repeated failures | Cluster patterns, scenario regression |

---

## Related plans

- `.cursor/plans/skill_feedback_api_2490d1a8.plan.md`
- Stack Calibration Studio concept: `stack_calibration_studio_4f36c161.plan.md`
