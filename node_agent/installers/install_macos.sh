#!/bin/sh
set -eu
install_root="$HOME/Library/Application Support/Kizuna"
agent="$HOME/Library/LaunchAgents/com.kizuna.node.plist"
mkdir -p "$install_root" "$HOME/Library/LaunchAgents"
cp "$(dirname "$0")/KizunaNode" "$install_root/KizunaNode"
chmod 755 "$install_root/KizunaNode"
cat > "$agent" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.kizuna.node</string>
<key>ProgramArguments</key><array><string>$install_root/KizunaNode</string><string>hive</string><string>--poll-seconds</string><string>3</string></array>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>$install_root/node.log</string>
<key>StandardErrorPath</key><string>$install_root/node-error.log</string>
</dict></plist>
EOF
echo "Kizuna Node installed. Enroll it before loading $agent with launchctl."

