# JPilot ↔ scstudio integration contract

Normative contract between **JPilot** (`backend-api`) and **Stack Calibration Studio** (`scstudio.nexxus-tech.com`).

**Canonical copy (scstudio repo):** [Nexxus-Tech-SAS/scstudio `docs/JPILOT_INTEGRATION.md`](https://github.com/Nexxus-Tech-SAS/scstudio/blob/main/docs/JPILOT_INTEGRATION.md)

**Customer-side implementation:** [CALIBRATION_SYNC.md](./CALIBRATION_SYNC.md)

**Last updated:** 2026-06-19

---

## Base URL

Production default: `https://scstudio.nexxus-tech.com` (`NEXXUS_CALIBRATION_BASE_URL`).

nginx (nexxus-web):

```nginx
location /skill-feedback {
    proxy_pass http://scstudio-backend-api:8000/skill-feedback;
}
location /calibrations/ {
    proxy_pass http://scstudio-backend-api:8000/calibrations/;
}
```

---

## Authentication

| Caller | Required fields |
|--------|-----------------|
| Licensed JPilot (Enterprise / Enterprise Pro) | `appFingerprint`, `installSignature` (future) |
| Free / Early Access | `appFingerprint` only |

JPilot derives `appFingerprint` from installation binding (`license_service.licensefingerprint()`).

Studio **human** sessions are separate — machine endpoints never use browser cookies.

---

## POST /calibrations/sync

Returns signed skill bundles and stack profile metadata for this install.

### Request

```json
{
  "appFingerprint": "<installation fingerprint>",
  "appName": "JPilot",
  "installSignature": "<optional base64url HMAC>",
  "timestamp": "2026-06-12T10:00:00Z",
  "nonce": "<random uuid>",
  "installedVersions": {
    "nexxus-netscaler-waf-tuning": "2.1.0"
  }
}
```

### Response (200)

```json
{
  "status": "active",
  "licenseType": "enterprise-pro",
  "clientId": "client-acme",
  "entitlements": ["blueprint_library", "calibration_studio"],
  "stackProfile": { "id": "acme-netscaler-2026", "version": "1.0.0" },
  "skills": [
    {
      "id": "nexxus-netscaler-waf-tuning",
      "version": "2.1.0",
      "packageSignature": "<Ed25519>",
      "bundleUrl": "/calibrations/bundles/nexxus-netscaler-waf-tuning/2.1.0"
    }
  ],
  "removed": ["deprecated-skill-id"]
}
```

### Tier gating (sync)

| JPilot license | Skills returned |
|----------------|-----------------|
| None / Early Access | `minTier: free` + `globalFreeSkill: true` only |
| Enterprise | free + enterprise assignments for client |
| Enterprise Pro | free + enterprise + enterprise_pro assignments |

**JPilot client:** `calibration_sync_service.sync_calibrations_from_studio` · local proxy `POST /copilot/calibrations/sync`

#### Knowledge Pack (v1 extension)

Sync request may include `installedKnowledgePack` (`id`, `version`, `contentHash`). Response may include `knowledgePack` (preferred) alongside transitional `skills[]`.

Full JPilot-side contract (local cache, verify, runtime assembly, UI): [CALIBRATION_SYNC.md — Knowledge Pack](./CALIBRATION_SYNC.md#knowledge-pack-knowpkg--jpilot-sync-contract-v1)

```json
{
  "knowledgePack": {
    "id": "nexxus-global",
    "version": "2.4.0",
    "contentHash": "sha256:...",
    "packageSignature": "<Ed25519>",
    "bundleUrl": "/calibrations/knowledge-packs/nexxus-global/2.4.0"
  },
  "stackProfile": { "knowledgePackVersion": "2.4.0" },
  "skills": []
}
```

---

## POST /calibrations/catalog

Read-only blueprint library metadata for agent discovery (no package download). Returns **all** published skills; each item includes `installable` and `ineligibleReason`. Sync still returns installable bundles only.

### Request

Same fields as sync (including `licenseCode` when the install has an activated license), plus optional vendor filter:

```json
{
  "appFingerprint": "<installation fingerprint>",
  "appName": "JPilot",
  "licenseCode": "<optional when licensed>",
  "vendor": "netscaler",
  "installedVersions": {}
}
```

### Response (200)

```json
{
  "catalogUrl": "https://scstudio.nexxus-tech.com/calibrations/catalog",
  "licenseType": "free",
  "clientId": null,
  "entitlements": [],
  "skills": [
    {
      "id": "nexxus-free-skill",
      "version": "1.0.0",
      "label": "Architect discovery",
      "vendor": "netscaler",
      "domains": ["architect", "discovery"],
      "minTier": "free",
      "globalFreeSkill": true,
      "installable": true,
      "ineligibleReason": null,
      "bundleUrl": "https://scstudio.nexxus-tech.com/calibrations/bundles/nexxus-free-skill/1.0.0"
    }
  ]
}
```

**JPilot enrichment:** local proxy `GET /copilot/calibrations/catalog` adds `installedBlueprints[]` by comparing the catalog with `data/calibrations/` (installed version, catalog version, `updateAvailable`).

**Chat agent tools:**

| Tool | Backing |
|------|---------|
| `list_official_blueprint_catalog` | `fetch_calibration_catalog` (+ `installedBlueprints`) |
| `search_stack_calibration_memory` | Installed skill memory modules only |

Agent rule: show all catalog skills; only recommend install when `installable` is true. Direct users to **Calibration Studio → Sync from Studio** or **Settings → Stack Calibrations** (`.calpkg` upload).

---

## POST /skill-feedback

JPilot sends end-user feedback about skill behavior. HTTP **202 Accepted**.

See [CALIBRATION_SYNC.md](./CALIBRATION_SYNC.md) for redaction rules and local proxy `POST /copilot/calibration-feedback`.

Categories: `wrong_tool`, `missing_step`, `wrong_answer`, `skill_not_triggered`, `too_slow`, `tool_limit`, `other`

---

## JPilot runtime (summary)

1. Sync or manual import → Knowledge Pack to `data/calibrations/knowledge-packs/` **or** legacy skills to `data/calibrations/{skillId}/{version}/`
2. MongoDB `knowledge_pack_state` + `stack_calibrations` index rows
3. **No SCStudio persona/assignment HTTP at chat time** — runtime reads active local pack only
4. Matcher: pack assembly (`knowledge_pack_runtime`) or legacy `calibration_matcher`; filter `skill.vendor == chat_vendor`, role; cap 2 skills/turn
5. **Blueprint-first:** server-side memory search + prompt injection before the LLM loop; gate blocks generic CLI/API tools when a blueprint matches until context is loaded (`copilot_calibration_gate`)
6. Platform gates (`copilot_memory_gate`, role tool allowlists) unchanged

See [CALIBRATION_SYNC.md](./CALIBRATION_SYNC.md) for Knowledge Pack details.

## Sample skill

[calibrations/samples/netscaler-firmware-ha-upgrade/](./calibrations/samples/netscaler-firmware-ha-upgrade/)
