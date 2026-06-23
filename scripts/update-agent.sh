#!/usr/bin/env sh
# JPilot host-side update agent.
#
# Invoked by jpilot-update-agent.path (systemd) when var/update/request.json
# appears.  Reads the sentinel, checks out the requested release tag, rebuilds
# the appropriate Docker Compose stack, then writes the final status back.
#
# Environment variables:
#   JPILOT_UPDATE_DIR   Override path to sentinel dir (default: <repo>/var/update)
#   DRY_RUN             Set to 1 to parse & validate without running git/docker
#   DOCKER_GROUP_USER   User to sudo-run compose as (optional, set by systemd unit)
#
# SECURITY NOTES:
#   - targetTag is validated against a strict semver regex before use.
#   - The agent never executes anything derived from the HTTP request body except
#     the validated tag.  All docker/git commands are hard-coded.
#   - The agent must run on the HOST (not inside a container); it needs the
#     Docker socket and git access.
#
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

UPDATE_DIR="${JPILOT_UPDATE_DIR:-${ROOT}/var/update}"
REQUEST_FILE="${UPDATE_DIR}/request.json"
STATUS_FILE="${UPDATE_DIR}/status.json"
DRY_RUN="${DRY_RUN:-0}"

COMPOSE_DEV="-f ${ROOT}/docker-compose.yml"
COMPOSE_PROD="-f ${ROOT}/docker-compose.yml -f ${ROOT}/docker-compose.prod.yml"

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

die() {
  log "FATAL: $*" >&2
  exit 1
}

write_status() {
  _state="$1"
  _tag="$2"
  _started="$3"
  _finished="$4"
  _progress_json="$5"
  _error="$6"

  if [ -n "$_error" ]; then
    _error_json="\"${_error}\""
  else
    _error_json="null"
  fi

  if [ -n "$_finished" ]; then
    _finished_json="\"${_finished}\""
  else
    _finished_json="null"
  fi

  cat > "${STATUS_FILE}" <<ENDJSON
{
  "state": "${_state}",
  "targetTag": "${_tag}",
  "startedAt": "${_started}",
  "finishedAt": ${_finished_json},
  "progress": ${_progress_json},
  "error": ${_error_json}
}
ENDJSON
}

append_progress() {
  _msg="$1"
  log "$_msg"
  # Append a new line to progress[] in status.json using python (always available).
  python3 - "${STATUS_FILE}" "$_msg" <<'PYEOF'
import json, sys
path, msg = sys.argv[1], sys.argv[2]
try:
    with open(path) as f:
        data = json.load(f)
except Exception:
    data = {}
data.setdefault("progress", []).append(msg)
with open(path, "w") as f:
    json.dump(data, f, indent=2)
PYEOF
}

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    die "Docker Compose not found."
  fi
}

# --------------------------------------------------------------------------
# Validate semver tag (defense-in-depth: the agent never checks out arbitrary refs)
# --------------------------------------------------------------------------
SEMVER_RE='^v?[0-9][0-9]*(\.[0-9][0-9]*)*$'

validate_tag() {
  _tag="$1"
  if printf '%s' "$_tag" | grep -Eq "$SEMVER_RE"; then
    return 0
  fi
  return 1
}

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

# Ensure sentinel dir exists.
mkdir -p "${UPDATE_DIR}"

# Check for request file.
if [ ! -f "${REQUEST_FILE}" ]; then
  log "No request.json found at ${REQUEST_FILE} — nothing to do."
  exit 0
fi

# Parse request.json.
TARGET_TAG=$(python3 -c "
import json, sys
with open('${REQUEST_FILE}') as f:
    d = json.load(f)
print(d.get('targetTag', ''))
" 2>/dev/null) || die "Could not parse request.json."

REQUESTED_AT=$(python3 -c "
import json, sys
with open('${REQUEST_FILE}') as f:
    d = json.load(f)
print(d.get('requestedAt', ''))
" 2>/dev/null) || REQUESTED_AT="unknown"

MODE=$(python3 -c "
import json, sys
with open('${REQUEST_FILE}') as f:
    d = json.load(f)
print(d.get('mode', 'dev'))
" 2>/dev/null) || MODE="dev"

log "Update request received: tag=${TARGET_TAG} mode=${MODE} requestedAt=${REQUESTED_AT}"

# Validate the tag — CRITICAL security check.
if ! validate_tag "${TARGET_TAG}"; then
  log "ERROR: targetTag '${TARGET_TAG}' does not match semver pattern — refusing update."
  NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  write_status "failed" "${TARGET_TAG}" "${REQUESTED_AT}" "${NOW}" '["Refused: targetTag failed semver validation."]' "targetTag failed semver validation: ${TARGET_TAG}"
  rm -f "${REQUEST_FILE}"
  exit 1
fi

# Set state=running.
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
write_status "running" "${TARGET_TAG}" "${REQUESTED_AT}" "" '["Starting update..."]' ""

if [ "${DRY_RUN}" = "1" ]; then
  log "DRY_RUN=1 — skipping git and docker commands."
  append_progress "DRY_RUN: would run: git fetch --tags origin"
  append_progress "DRY_RUN: would run: git checkout ${TARGET_TAG}"
  if [ "${MODE}" = "prod" ] || [ "${MODE}" = "production" ]; then
    append_progress "DRY_RUN: would run: docker compose ${COMPOSE_PROD} build"
    append_progress "DRY_RUN: would run: docker compose ${COMPOSE_PROD} up -d"
  else
    append_progress "DRY_RUN: would run: docker compose ${COMPOSE_DEV} build"
    append_progress "DRY_RUN: would run: docker compose ${COMPOSE_DEV} up -d"
  fi
  FINISHED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  write_status "success" "${TARGET_TAG}" "${REQUESTED_AT}" "${FINISHED}" '["DRY_RUN completed — no actual changes made."]' ""
  rm -f "${REQUEST_FILE}"
  log "DRY_RUN complete."
  exit 0
fi

# ---------- Real update path ----------

set +e  # We handle errors manually from here.

run_update() {
  append_progress "Fetching tags from origin..."
  if ! git fetch --tags origin; then
    append_progress "ERROR: git fetch --tags origin failed."
    return 1
  fi

  append_progress "Checking out ${TARGET_TAG}..."
  if ! git checkout "${TARGET_TAG}"; then
    append_progress "ERROR: git checkout ${TARGET_TAG} failed."
    return 1
  fi

  if [ "${MODE}" = "prod" ] || [ "${MODE}" = "production" ]; then
    COMPOSE_FLAGS="${COMPOSE_PROD}"
    append_progress "Rebuilding production stack..."
  else
    COMPOSE_FLAGS="${COMPOSE_DEV}"
    append_progress "Rebuilding development stack..."
  fi

  # shellcheck disable=SC2086
  if ! compose_cmd $COMPOSE_FLAGS build; then
    append_progress "ERROR: docker compose build failed."
    return 1
  fi

  append_progress "Bringing stack up..."
  # shellcheck disable=SC2086
  if ! compose_cmd $COMPOSE_FLAGS up -d; then
    append_progress "ERROR: docker compose up -d failed."
    return 1
  fi

  return 0
}

if run_update; then
  FINISHED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  write_status "success" "${TARGET_TAG}" "${REQUESTED_AT}" "${FINISHED}" '["Update completed successfully."]' ""
  rm -f "${REQUEST_FILE}"
  log "Update to ${TARGET_TAG} completed successfully."
else
  FINISHED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  # Capture last progress lines from current status file.
  PREV_PROGRESS=$(python3 -c "
import json, sys
try:
    with open('${STATUS_FILE}') as f:
        d = json.load(f)
    print(json.dumps(d.get('progress', [])))
except Exception:
    print('[]')
" 2>/dev/null) || PREV_PROGRESS='["Update failed — see host logs."]'
  python3 - "${STATUS_FILE}" "${TARGET_TAG}" "${REQUESTED_AT}" "${FINISHED}" "${PREV_PROGRESS}" <<'PYEOF'
import json, sys
path, tag, started, finished, progress_json = sys.argv[1:]
try:
    progress = json.loads(progress_json)
except Exception:
    progress = []
data = {
    "state": "failed",
    "targetTag": tag,
    "startedAt": started,
    "finishedAt": finished,
    "progress": progress,
    "error": "Update failed — check host system logs (journalctl -u jpilot-update-agent.service).",
}
with open(path, "w") as f:
    json.dump(data, f, indent=2)
PYEOF
  rm -f "${REQUEST_FILE}"
  log "Update to ${TARGET_TAG} FAILED."
  exit 1
fi
