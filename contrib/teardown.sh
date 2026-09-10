#!/usr/bin/env bash
set -euo pipefail
systemctl --user disable --now okbayd.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/okbayd.service"
echo "Daemon stopped. Workspace ~/Work/okbay was left on disk."
