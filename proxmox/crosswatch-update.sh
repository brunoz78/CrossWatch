#!/usr/bin/env bash
# crosswatch-update - install or update CrossWatch (brunoz78/CrossWatch) in this container.
#
#   crosswatch-update            update to the latest release if it is newer
#   crosswatch-update --force    reinstall the latest release
#   crosswatch-update --install  first installation (no running service yet)
#   crosswatch-update --from-ui  started by the "Update now" button (systemd path unit)
#
# The release asset crosswatch-<tag>.tar.gz contains the code, VERSION and a
# hash-pinned requirements.lock. The previous version is kept in
# /opt/crosswatch.old and restored automatically if the new one does not start.
set -Eeuo pipefail

REPO="${CW_REPO:-brunoz78/CrossWatch}"
APP_DIR="/opt/crosswatch"
DATA_DIR="/var/lib/crosswatch"
BACKUP_DIR="/var/backups/crosswatch"
UPD_DIR="${DATA_DIR}/.update"
STATUS="${UPD_DIR}/status.json"
PORT="${WEB_PORT:-8787}"

MODE="update"
case "${1:-}" in
  --force) MODE="force" ;;
  --install) MODE="install" ;;
  --from-ui) MODE="ui" ;;
  "") ;;
  *) echo "Usage: crosswatch-update [--force|--install|--from-ui]" >&2; exit 2 ;;
esac

mkdir -p "$UPD_DIR" "$BACKUP_DIR"
rm -f "${UPD_DIR}/request"
STARTED=$(date +%s)
CURRENT=$(cat "${APP_DIR}/VERSION" 2>/dev/null || echo "none")

status() { # state message [to]
  jq -n --arg state "$1" --arg message "$2" --arg from "$CURRENT" --arg to "${3:-}" \
    --argjson started "$STARTED" --argjson finished "$(date +%s)" \
    '{state:$state,message:$message,from:$from,to:$to,started_at:$started,finished_at:$finished}' >"${STATUS}.tmp"
  mv "${STATUS}.tmp" "$STATUS"
}
log() { echo "[crosswatch-update] $*"; }
fail() { log "ERROR: $*"; status failed "$*" "${LATEST:-}"; exit 1; }

status running "Checking for a new release"
RELEASE=$(curl -fsSL -H "Accept: application/vnd.github+json" "https://api.github.com/repos/${REPO}/releases/latest") \
  || fail "GitHub is not reachable"
LATEST=$(jq -r '.tag_name' <<<"$RELEASE")
ASSET_URL=$(jq -r --arg n "crosswatch-${LATEST}.tar.gz" '.assets[] | select(.name==$n) | .browser_download_url' <<<"$RELEASE")
SHA_URL=$(jq -r --arg n "crosswatch-${LATEST}.tar.gz.sha256" '.assets[] | select(.name==$n) | .browser_download_url' <<<"$RELEASE")
[[ -n "$LATEST" && "$LATEST" != "null" && -n "$ASSET_URL" ]] || fail "Release ${LATEST} has no installable archive"

if [[ "$MODE" == "update" || "$MODE" == "ui" ]] && [[ "$CURRENT" == "$LATEST" ]]; then
  log "Already up to date (${CURRENT})"
  status done "Already up to date" "$LATEST"
  exit 0
fi

log "Installing ${LATEST} (installed: ${CURRENT})"
status running "Downloading ${LATEST}" "$LATEST"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
curl -fsSL -o "${TMP}/cw.tar.gz" "$ASSET_URL" || fail "Download failed"
if [[ -n "$SHA_URL" ]]; then
  curl -fsSL -o "${TMP}/cw.sha256" "$SHA_URL" || fail "Checksum download failed"
  (cd "$TMP" && echo "$(cut -d' ' -f1 cw.sha256)  cw.tar.gz" | sha256sum -c --quiet -) || fail "Checksum does not match"
fi

status running "Preparing ${LATEST}" "$LATEST"
NEW="${APP_DIR}.new"
rm -rf "$NEW"
mkdir -p "$NEW"
tar -xzf "${TMP}/cw.tar.gz" -C "$NEW" --strip-components=1 || fail "Archive could not be unpacked"
python3 -m venv "${NEW}/.venv" || fail "Python environment could not be created"
"${NEW}/.venv/bin/pip" install -q --upgrade pip >/dev/null || fail "pip could not be updated"
"${NEW}/.venv/bin/pip" install -q --require-hashes --no-deps -r "${NEW}/requirements.lock" || fail "Dependencies could not be installed"
install -m 755 "${NEW}/proxmox/crosswatch-update.sh" /usr/local/bin/crosswatch-update.new

status running "Switching to ${LATEST}" "$LATEST"
if [[ "$MODE" != "install" ]]; then
  # Data stays in place; this copy is only a safety net.
  tar -czf "${BACKUP_DIR}/data-$(date +%Y%m%d-%H%M%S).tar.gz" -C "$DATA_DIR" \
    --exclude=./.update --exclude=./cache . 2>/dev/null || log "Data backup incomplete"
  ls -1t "${BACKUP_DIR}"/data-*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f
  systemctl stop crosswatch || true
fi
rm -rf "${APP_DIR}.old"
[[ -d "$APP_DIR" ]] && mv "$APP_DIR" "${APP_DIR}.old"
mv "$NEW" "$APP_DIR"
mv /usr/local/bin/crosswatch-update.new /usr/local/bin/crosswatch-update

if [[ "$MODE" == "install" ]]; then
  status done "Installed ${LATEST}" "$LATEST"
  exit 0
fi

systemctl start crosswatch
for _ in $(seq 1 60); do
  if curl -fsS -o /dev/null "http://127.0.0.1:${PORT}/healthz" || curl -fsS -o /dev/null "http://127.0.0.1:${PORT}/api/health"; then
    log "Updated to ${LATEST}"
    status done "Updated to ${LATEST}" "$LATEST"
    exit 0
  fi
  sleep 2
done

log "New version does not answer, rolling back to ${CURRENT}"
systemctl stop crosswatch || true
if [[ -d "${APP_DIR}.old" ]]; then
  rm -rf "${APP_DIR}.failed"
  mv "$APP_DIR" "${APP_DIR}.failed"
  mv "${APP_DIR}.old" "$APP_DIR"
  systemctl start crosswatch || true
fi
fail "Version ${LATEST} did not start, ${CURRENT} was restored"
