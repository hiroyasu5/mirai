#!/bin/bash
# MIRAI systemd timer インストールスクリプト
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== MIRAI systemd timer インストール ==="

# ユニットファイルをコピー
sudo cp "$SCRIPT_DIR/mirai-forecast.service" /etc/systemd/system/
sudo cp "$SCRIPT_DIR/mirai-forecast.timer" /etc/systemd/system/

# systemd リロード
sudo systemctl daemon-reload

# タイマー有効化・起動
sudo systemctl enable mirai-forecast.timer
sudo systemctl start mirai-forecast.timer

echo ""
echo "=== インストール完了 ==="
echo ""
systemctl status mirai-forecast.timer --no-pager
echo ""
echo "次回実行予定:"
systemctl list-timers mirai-forecast.timer --no-pager
