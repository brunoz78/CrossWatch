#!/usr/bin/env bash
# Engine comes from community-scripts/core; this repo only ships the scripts.
# A local core checkout wins (COMMUNITY_SCRIPTS_CORE_DIR, else a sibling ../core),
# so a fork or branch of core can be tested without editing this file.
_cs_boot="${COMMUNITY_SCRIPTS_CORE_DIR:-$(dirname "${BASH_SOURCE[0]}")/../../core}/core/build.func"
source "$_cs_boot" 2>/dev/null || source <(curl -fsSL "${COMMUNITY_SCRIPTS_CORE_URL:-https://raw.githubusercontent.com/community-scripts/core/main}/core/build.func")
# Copyright (c) 2021-2026 community-scripts ORG
# Author: brunoz78
# License: MIT | https://github.com/community-scripts/ProxmoxVED/raw/main/LICENSE
# Source: https://github.com/brunoz78/CrossWatch

APP="CrossWatch"
var_tags="${var_tags:-media;sync}"
var_cpu="${var_cpu:-2}"
var_ram="${var_ram:-1024}"
var_disk="${var_disk:-8}"
var_os="${var_os:-debian}"
var_version="${var_version:-13}"
var_unprivileged="${var_unprivileged:-1}"

header_info "$APP"
variables
color
catch_errors

function update_script() {
  header_info
  check_container_storage
  check_container_resources

  if [[ ! -d /opt/crosswatch ]]; then
    msg_error "No ${APP} Installation Found!"
    exit
  fi

  # Same code path as the "Update now" button in the web interface:
  # download, verify, switch, health check, automatic rollback.
  msg_info "Updating ${APP}"
  if crosswatch-update; then
    msg_ok "$(jq -r '.message' /config/.update/status.json)"
  else
    msg_error "$(jq -r '.message' /config/.update/status.json)"
  fi
  exit
}

start
build_container
description

msg_ok "Completed Successfully!\n"
echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
echo -e "${INFO}${YW}Open this one-time setup link to create the admin account:${CL}"
echo -e "${GATEWAY}${BGN}http://${IP}:8787/?setup=$(pct exec "$CTID" -- cat /config/.setup_token)${CL}"
