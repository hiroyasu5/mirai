"""
Discord Webhook 通知
レポートをDiscordに送信する（Webhook方式、Bot不要）
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

DISCORD_MAX_LENGTH = 2000


class DiscordNotifier:
    """Discord Webhookでレポートを通知"""

    def __init__(self, config: dict):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        self.max_length = config.get("discord", {}).get("max_message_length", DISCORD_MAX_LENGTH)

    def send_report(self, report: str) -> bool:
        """レポートをDiscordに送信（長文は分割）"""
        if not self.webhook_url:
            logger.warning("DISCORD_WEBHOOK_URL が設定されていません。通知スキップ。")
            return False

        chunks = self._split_message(report)
        logger.info(f"Discord送信: {len(chunks)}メッセージに分割")

        success = True
        for i, chunk in enumerate(chunks):
            if not self._send_chunk(chunk, i + 1, len(chunks)):
                success = False

        return success

    def _split_message(self, text: str) -> list[str]:
        """テキストをDiscordの文字数制限に合わせて分割"""
        if len(text) <= self.max_length:
            return [text]

        chunks = []
        remaining = text

        while remaining:
            if len(remaining) <= self.max_length:
                chunks.append(remaining)
                break

            # 改行位置で分割
            split_point = remaining.rfind("\n", 0, self.max_length)
            if split_point == -1 or split_point < self.max_length // 2:
                split_point = self.max_length

            chunks.append(remaining[:split_point])
            remaining = remaining[split_point:].lstrip("\n")

        return chunks

    def _send_chunk(self, content: str, part: int, total: int) -> bool:
        """1チャンクをDiscordに送信"""
        payload = {"content": content}

        if total > 1:
            payload["content"] = f"**[{part}/{total}]**\n{content}"
            # 分割後も制限超えないようトリム
            if len(payload["content"]) > self.max_length:
                payload["content"] = payload["content"][:self.max_length - 3] + "..."

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            logger.info(f"Discord送信成功 ({part}/{total})")
            return True
        except requests.RequestException as e:
            logger.error(f"Discord送信エラー ({part}/{total}): {e}")
            return False
