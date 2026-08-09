#!/bin/sh
set -eu
install_root="$HOME/.local/bin"
service_root="$HOME/.config/systemd/user"
mkdir -p "$install_root" "$service_root"
cp "$(dirname "$0")/KizunaNode" "$install_root/kizuna-node"
chmod 755 "$install_root/kizuna-node"
cat > "$service_root/kizuna-node.service" <<EOF
[Unit]
Description=Kizuna mixed-platform Hive companion
After=network-online.target
[Service]
ExecStart=$install_root/kizuna-node hive --poll-seconds 3
Restart=on-failure
RestartSec=5
[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
echo "Kizuna Node installed. Enroll it, then run: systemctl --user enable --now kizuna-node"

