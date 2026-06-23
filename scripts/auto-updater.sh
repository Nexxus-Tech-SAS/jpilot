#!/usr/bin/env sh
# JPilot auto-updater configurator.
#
# Installs or removes the systemd path+service units that let the in-app
# "Update" button trigger a host-side rebuild. Paths are auto-detected from this
# script's own location (the JPilot repo) and the docker-group user — no manual
# editing of unit files.
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

SERVICE_NAME="jpilot-update-agent"
SYSTEMD_DIR="/etc/systemd/system"
PATH_UNIT="${SYSTEMD_DIR}/${SERVICE_NAME}.path"
SERVICE_UNIT="${SYSTEMD_DIR}/${SERVICE_NAME}.service"

# ── Detect the docker-group user (run-as for the agent) ──────────────────────
detect_user() {
  if [ -n "${DOCKER_USER:-}" ]; then
    printf '%s' "${DOCKER_USER}"
  elif [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    printf '%s' "${SUDO_USER}"
  elif [ "$(id -un)" != "root" ]; then
    printf '%s' "$(id -un)"
  else
    stat -c '%U' "${JPILOT_DIR}" 2>/dev/null || printf 'root'
  fi
}
RUN_USER=$(detect_user)

# ── sudo helper (no-op when already root) ────────────────────────────────────
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "ERROR: systemd changes need root. Re-run as root or install sudo." >&2
    exit 1
  fi
fi

have_systemd() { command -v systemctl >/dev/null 2>&1; }
user_in_docker_group() { id -nG "$1" 2>/dev/null | tr ' ' '\n' | grep -qx docker; }

# ── Unit generation ──────────────────────────────────────────────────────────
write_units() {
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

clean_agent() {
  echo "==> Cleaning any existing agent units..."
  if have_systemd; then
    $SUDO systemctl disable --now "${SERVICE_NAME}.path" >/dev/null 2>&1 || true
    $SUDO systemctl stop "${SERVICE_NAME}.service" >/dev/null 2>&1 || true
  fi
  $SUDO rm -f "${PATH_UNIT}" "${SERVICE_UNIT}"
  if have_systemd; then $SUDO systemctl daemon-reload || true; fi
}

enable_auto_update() {
  if ! have_systemd; then
    echo "systemd not found. On non-systemd hosts run the agent manually:"
    echo "    cd ${JPILOT_DIR} && sh scripts/update-agent.sh"
    return 1
  fi
  if [ ! -f "${AGENT_SCRIPT}" ]; then
    echo "ERROR: agent script not found at ${AGENT_SCRIPT}" >&2
    return 1
  fi
  if ! user_in_docker_group "${RUN_USER}"; then
    echo "WARNING: user '${RUN_USER}' is not in the 'docker' group — the agent may"
    echo "         not be able to run 'docker compose'. Set DOCKER_USER=<user> to override."
  fi
  mkdir -p "${UPDATE_DIR}"
  clean_agent                       # always clean the old agent first
  write_units
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable --now "${SERVICE_NAME}.path"
  echo "==> Auto-update ENABLED."
  status_auto_update
}

disable_auto_update() {
  clean_agent
  echo "==> Auto-update DISABLED."
}

status_auto_update() {
  state="disabled"
  if have_systemd && systemctl is-enabled "${SERVICE_NAME}.path" >/dev/null 2>&1; then
    state="ENABLED (watcher: $(systemctl is-active "${SERVICE_NAME}.path" 2>/dev/null))"
  fi
  echo "----------------------------------------------------------"
  echo " JPilot install : ${JPILOT_DIR}"
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
    3) $SUDO journalctl -u "${SERVICE_NAME}.service" -n 25 --no-pager 2>/dev/null || echo "(no journal)" ;;
    q|quit|exit) exit 0 ;;
    *) echo "Invalid choice." ;;
  esac
done
