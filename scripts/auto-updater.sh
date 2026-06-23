#!/usr/bin/env sh
# JPilot auto-updater configurator.
#
# Installs or removes the host watcher that lets the in-app "Update" button trigger
# a rebuild. Linux uses systemd path+service units; macOS uses a LaunchAgent.
# Paths are auto-detected from this script's location — no manual editing.
#
# Usage:
#   ./scripts/auto-updater.sh            # interactive menu
#   ./scripts/auto-updater.sh enable     # install + start the agent
#   ./scripts/auto-updater.sh disable    # stop + remove the agent
#   ./scripts/auto-updater.sh status     # show current state
#
# Override the run-as user with:  DOCKER_USER=someuser ./scripts/auto-updater.sh enable
set -u

# ── Resolve paths from this script's location ────────────────────────────────
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
JPILOT_DIR=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
AGENT_SCRIPT="${JPILOT_DIR}/scripts/update-agent.sh"
UPDATE_DIR="${JPILOT_DIR}/var/update"
AGENT_ARMED_MARKER="${UPDATE_DIR}/.agent-armed"
AGENT_LOG="${UPDATE_DIR}/agent.log"

# Detect the Docker Compose root: a standalone JPilot install uses the repo itself;
# the unified Nexxus stack is orchestrated by the parent dir's docker-compose.yml
# (which runs jpilot + scstudio together). The agent rebuilds from this root.
PARENT_DIR=$(CDPATH= cd -- "${JPILOT_DIR}/.." && pwd)
if [ -f "${PARENT_DIR}/docker-compose.yml" ] && grep -q "jpilot" "${PARENT_DIR}/docker-compose.yml" 2>/dev/null; then
  COMPOSE_ROOT="${PARENT_DIR}"
  DEPLOY_MODE="unified"
else
  COMPOSE_ROOT="${JPILOT_DIR}"
  DEPLOY_MODE="standalone"
fi
COMPOSE_ROOT="${JPILOT_COMPOSE_ROOT:-${COMPOSE_ROOT}}"

SERVICE_NAME="jpilot-update-agent"
LAUNCHD_LABEL="com.nexxus.jpilot-update-agent"
SYSTEMD_DIR="/etc/systemd/system"
PATH_UNIT="${SYSTEMD_DIR}/${SERVICE_NAME}.path"
SERVICE_UNIT="${SYSTEMD_DIR}/${SERVICE_NAME}.service"

# ── Detect the docker-group user (run-as for the agent) ──────────────────────
dir_owner() {
  if stat -c '%U' "$1" >/dev/null 2>&1; then
    stat -c '%U' "$1"
  else
    stat -f '%Su' "$1"
  fi
}

detect_user() {
  if [ -n "${DOCKER_USER:-}" ]; then
    printf '%s' "${DOCKER_USER}"
  elif [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    printf '%s' "${SUDO_USER}"
  elif [ "$(id -un)" != "root" ]; then
    printf '%s' "$(id -un)"
  else
    dir_owner "${JPILOT_DIR}" 2>/dev/null || printf 'root'
  fi
}
RUN_USER=$(detect_user)

# ── Platform helpers ─────────────────────────────────────────────────────────
have_systemd() { command -v systemctl >/dev/null 2>&1 && [ "$(uname -s)" != "Darwin" ]; }
have_launchd() { [ "$(uname -s)" = "Darwin" ] && command -v launchctl >/dev/null 2>&1; }
user_in_docker_group() { id -nG "$1" 2>/dev/null | tr ' ' '\n' | grep -qx docker; }

launchd_plist_path() {
  printf '%s/Library/LaunchAgents/%s.plist' "${HOME}" "${LAUNCHD_LABEL}"
}

launchd_domain() {
  printf 'gui/%s' "$(id -u)"
}

# ── sudo helper (Linux systemd only) ─────────────────────────────────────────
SUDO=""
needs_sudo_for_systemd() {
  have_systemd && [ "$(id -u)" -ne 0 ]
}

if needs_sudo_for_systemd; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "ERROR: systemd changes need root. Re-run as root or install sudo." >&2
    exit 1
  fi
fi

mark_agent_armed() {
  mkdir -p "${UPDATE_DIR}"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${AGENT_ARMED_MARKER}"
}

clear_agent_armed() {
  rm -f "${AGENT_ARMED_MARKER}"
}

# ── systemd (Linux) ──────────────────────────────────────────────────────────
write_systemd_units() {
  echo "==> Writing systemd units"
  echo "      install dir : ${JPILOT_DIR}"
  echo "      run as user : ${RUN_USER}"
  echo "      watch file  : ${UPDATE_DIR}/request.json"
  $SUDO tee "${PATH_UNIT}" >/dev/null <<EOF
[Unit]
Description=JPilot update-request sentinel watcher
Documentation=https://github.com/Nexxus-Tech-SAS/jpilot

[Path]
PathExists=${UPDATE_DIR}/request.json
PathModified=${UPDATE_DIR}/request.json
Unit=${SERVICE_NAME}.service

[Install]
WantedBy=multi-user.target
EOF

  $SUDO tee "${SERVICE_UNIT}" >/dev/null <<EOF
[Unit]
Description=JPilot one-click self-update agent
Documentation=https://github.com/Nexxus-Tech-SAS/jpilot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=${RUN_USER}
Group=docker
WorkingDirectory=${JPILOT_DIR}
Environment=JPILOT_UPDATE_DIR=${UPDATE_DIR}
Environment=JPILOT_COMPOSE_ROOT=${COMPOSE_ROOT}
ExecStart=/bin/sh ${AGENT_SCRIPT}
TimeoutStartSec=600
Restart=no
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

[Install]
WantedBy=multi-user.target
EOF
}

clean_systemd_agent() {
  if ! have_systemd; then
    return 0
  fi
  $SUDO systemctl disable --now "${SERVICE_NAME}.path" >/dev/null 2>&1 || true
  $SUDO systemctl stop "${SERVICE_NAME}.service" >/dev/null 2>&1 || true
  $SUDO rm -f "${PATH_UNIT}" "${SERVICE_UNIT}"
  $SUDO systemctl daemon-reload || true
}

enable_systemd_agent() {
  if [ ! -f "${AGENT_SCRIPT}" ]; then
    echo "ERROR: agent script not found at ${AGENT_SCRIPT}" >&2
    return 1
  fi
  if ! user_in_docker_group "${RUN_USER}"; then
    echo "WARNING: user '${RUN_USER}' is not in the 'docker' group — the agent may"
    echo "         not be able to run 'docker compose'. Set DOCKER_USER=<user> to override."
  fi
  mkdir -p "${UPDATE_DIR}"
  clean_systemd_agent
  write_systemd_units
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable --now "${SERVICE_NAME}.path"
  mark_agent_armed
  echo "==> Auto-update ENABLED (systemd)."
}

# ── launchd (macOS) ──────────────────────────────────────────────────────────
write_launchd_plist() {
  plist_path=$(launchd_plist_path)
  echo "==> Writing LaunchAgent"
  echo "      install dir : ${JPILOT_DIR}"
  echo "      run as user : ${RUN_USER}"
  echo "      watch file  : ${UPDATE_DIR}/request.json"
  echo "      plist       : ${plist_path}"
  mkdir -p "${UPDATE_DIR}" "${HOME}/Library/LaunchAgents"
  cat > "${plist_path}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LAUNCHD_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>${AGENT_SCRIPT}</string>
  </array>
  <key>WatchPaths</key>
  <array>
    <string>${UPDATE_DIR}/request.json</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>JPILOT_UPDATE_DIR</key>
    <string>${UPDATE_DIR}</string>
    <key>JPILOT_COMPOSE_ROOT</key>
    <string>${COMPOSE_ROOT}</string>
  </dict>
  <key>StandardOutPath</key>
  <string>${AGENT_LOG}</string>
  <key>StandardErrorPath</key>
  <string>${AGENT_LOG}</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
EOF
}

clean_launchd_agent() {
  if ! have_launchd; then
    return 0
  fi
  plist_path=$(launchd_plist_path)
  domain=$(launchd_domain)
  launchctl bootout "${domain}" "${plist_path}" >/dev/null 2>&1 || true
  rm -f "${plist_path}"
}

enable_launchd_agent() {
  if [ ! -f "${AGENT_SCRIPT}" ]; then
    echo "ERROR: agent script not found at ${AGENT_SCRIPT}" >&2
    return 1
  fi
  mkdir -p "${UPDATE_DIR}" "${HOME}/Library/LaunchAgents"
  clean_launchd_agent
  write_launchd_plist
  plist_path=$(launchd_plist_path)
  domain=$(launchd_domain)
  if ! launchctl bootstrap "${domain}" "${plist_path}"; then
    echo "ERROR: launchctl bootstrap failed for ${plist_path}" >&2
    return 1
  fi
  mark_agent_armed
  echo "==> Auto-update ENABLED (launchd)."
  echo "    Agent log: ${AGENT_LOG}"
}

# ── Shared enable/disable/status ─────────────────────────────────────────────
clean_agent() {
  echo "==> Cleaning any existing agent watchers..."
  clean_systemd_agent
  clean_launchd_agent
  clear_agent_armed
}

enable_auto_update() {
  if have_systemd; then
    enable_systemd_agent || return 1
  elif have_launchd; then
    enable_launchd_agent || return 1
  else
    echo "No supported service manager found (systemd or launchd)."
    echo "Run the agent manually when you click Update:"
    echo "    cd ${JPILOT_DIR} && sh scripts/update-agent.sh"
    return 1
  fi
  status_auto_update
}

disable_auto_update() {
  clean_agent
  echo "==> Auto-update DISABLED."
}

systemd_state() {
  if have_systemd && systemctl is-enabled "${SERVICE_NAME}.path" >/dev/null 2>&1; then
    printf 'ENABLED (systemd watcher: %s)' "$(systemctl is-active "${SERVICE_NAME}.path" 2>/dev/null)"
    return 0
  fi
  return 1
}

launchd_state() {
  if ! have_launchd; then
    return 1
  fi
  plist_path=$(launchd_plist_path)
  if [ ! -f "${plist_path}" ]; then
    return 1
  fi
  domain=$(launchd_domain)
  if launchctl print "${domain}/${LAUNCHD_LABEL}" >/dev/null 2>&1; then
    printf 'ENABLED (launchd watcher loaded)'
    return 0
  fi
  printf 'PARTIAL (plist installed but not loaded — re-run enable)'
  return 0
}

status_auto_update() {
  state="disabled"
  if systemd_state >/dev/null 2>&1; then
    state=$(systemd_state)
  elif launchd_state >/dev/null 2>&1; then
    state=$(launchd_state)
  elif [ -f "${AGENT_ARMED_MARKER}" ]; then
    state="MARKER ONLY (watcher missing — re-run enable)"
  fi
  echo "----------------------------------------------------------"
  echo " JPilot install : ${JPILOT_DIR}"
  echo " Deployment     : ${DEPLOY_MODE} (compose root: ${COMPOSE_ROOT})"
  echo " Run-as user    : ${RUN_USER}"
  echo " Sentinel dir   : ${UPDATE_DIR}"
  echo " Auto-update    : ${state}"
  echo "----------------------------------------------------------"
}

# ── CLI args (non-interactive) ───────────────────────────────────────────────
case "${1:-}" in
  enable)  enable_auto_update;  exit $? ;;
  disable) disable_auto_update; exit 0 ;;
  status)  status_auto_update;  exit 0 ;;
  "" )     : ;;  # fall through to menu
  * )      echo "Usage: $0 [enable|disable|status]" >&2; exit 2 ;;
esac

# ── Interactive menu ─────────────────────────────────────────────────────────
while true; do
  echo ""
  echo "============== JPilot auto-updater =============="
  status_auto_update
  echo "  1) Enable auto-update   (install + start the host agent)"
  echo "  2) Disable auto-update  (stop + remove the host agent)"
  echo "  3) Show recent agent log"
  echo "  q) Quit"
  printf "Choose [1/2/3/q]: "
  if ! IFS= read -r choice; then echo; exit 0; fi
  case "$(printf '%s' "$choice" | tr '[:upper:]' '[:lower:]')" in
    1) enable_auto_update || true ;;
    2) disable_auto_update || true ;;
    3)
      if [ -f "${AGENT_LOG}" ]; then
        tail -n 25 "${AGENT_LOG}"
      else
        $SUDO journalctl -u "${SERVICE_NAME}.service" -n 25 --no-pager 2>/dev/null || echo "(no agent log yet)"
      fi
      ;;
    q|quit|exit) exit 0 ;;
    *) echo "Invalid choice." ;;
  esac
done
