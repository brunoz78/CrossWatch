#!/usr/bin/env bash

# Copyright (c) 2021-2026 community-scripts ORG
# Author: brunoz78
# License: MIT | https://github.com/community-scripts/ProxmoxVED/raw/main/LICENSE
# Source: https://github.com/brunoz78/CrossWatch

source /dev/stdin <<<"$FUNCTIONS_FILE_PATH"
color
verb_ip6
catch_errors
setting_up_container
network_check
update_os

msg_info "Installing Dependencies"
$STD apt install -y python3 python3-venv jq curl ca-certificates tzdata
msg_ok "Installed Dependencies"

msg_info "Installing CrossWatch"
mkdir -p /var/lib/crosswatch
chmod 700 /var/lib/crosswatch
curl -fsSL -o /usr/local/bin/crosswatch-update \
  "https://raw.githubusercontent.com/brunoz78/CrossWatch/main/proxmox/crosswatch-update.sh"
chmod 755 /usr/local/bin/crosswatch-update
$STD crosswatch-update --install
msg_ok "Installed CrossWatch $(cat /opt/crosswatch/VERSION)"

msg_info "Creating Services"
cat <<SVC >/etc/systemd/system/crosswatch.service
[Unit]
Description=CrossWatch
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/crosswatch
Environment=CONFIG_BASE=/var/lib/crosswatch
Environment=WEB_PORT=8787
Environment=TZ=Europe/Zurich
Environment=CW_UI_LANG=de
Environment=CW_UPDATER=systemd
Environment=GITHUB_REPO=brunoz78/CrossWatch
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/opt/crosswatch/.venv/bin/python -m crosswatch
Restart=on-failure
RestartSec=5
# The app only writes to its data directory.
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/var/lib/crosswatch

[Install]
WantedBy=multi-user.target
SVC

# "Update now" in the web interface drops a request file; this runs the update as root.
cat <<SVC >/etc/systemd/system/crosswatch-update.path
[Unit]
Description=Watch for CrossWatch update requests

[Path]
PathExists=/var/lib/crosswatch/.update/request
MakeDirectory=yes

[Install]
WantedBy=multi-user.target
SVC

cat <<SVC >/etc/systemd/system/crosswatch-update.service
[Unit]
Description=Update CrossWatch to the latest release

[Service]
Type=oneshot
ExecStart=/usr/local/bin/crosswatch-update --from-ui
SVC
systemctl enable -q --now crosswatch crosswatch-update.path
msg_ok "Created Services"

msg_info "Waiting for first start"
for _ in $(seq 1 60); do
  [[ -s /var/lib/crosswatch/.setup_token ]] && break
  sleep 2
done
msg_ok "CrossWatch is running"

motd_ssh
customize
cleanup_lxc
