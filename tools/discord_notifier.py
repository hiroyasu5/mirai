"""
Discord Webhook 通知
レポートをDiscordに送信する（Webhook方式、Bot不要）
Embed形式のdailyレポート送信にも対応
フルレポートはEmbed要約+HTMLファイル添付で送信
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DISCORD_MAX_LENGTH = 2000

# ドメイン別の色と絵文字
DOMAIN_THEMES = {
    "tech": {
        "color": 0x3498DB,  # 青
        "emoji": "🔬",
        "label": "テクノロジー",
    },
    "econ": {
        "color": 0xF1C40F,  # 黄
        "emoji": "📊",
        "label": "経済・マーケット",
    },
    "social": {
        "color": 0x2ECC71,  # 緑
        "emoji": "🌍",
        "label": "社会・文化",
    },
}


class DiscordNotifier:
    """Discord Webhookでレポートを通知"""

    def __init__(self, config: dict):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        self.max_length = config.get("discord", {}).get("max_message_length", DISCORD_MAX_LENGTH)

    def send_daily_embed(self, domain: str, report_data: dict, report_url: str | None = None) -> bool:
        """Embed形式でdailyレポートを送信"""
        if not self.webhook_url:
            logger.warning("DISCORD_WEBHOOK_URL が設定されていません。通知スキップ。")
            return False

        theme = DOMAIN_THEMES.get(domain, DOMAIN_THEMES["tech"])
        today = datetime.now().strftime("%Y年%m月%d日")

        # Embed構築
        embed = {
            "title": f"{theme['emoji']} {report_data.get('title', '今日の' + theme['label'] + '予測')}",
            "description": report_data.get("summary", ""),
            "color": theme["color"],
            "fields": [],
            "footer": {"text": f"MIRAI 未来予測 • {datetime.now().strftime('%Y/%m/%d')}"},
            "timestamp": datetime.utcnow().isoformat(),
        }
        if report_url:
            embed["url"] = report_url

        # 注目ニュース
        news_items = report_data.get("news", [])
        if news_items:
            news_lines = []
            for item in news_items:
                headline = item.get("headline", "")
                url = item.get("url", "")
                detail = item.get("detail", "")
                if url:
                    news_lines.append(f"[**{headline}**]({url})\n{detail}")
                else:
                    news_lines.append(f"**{headline}**\n{detail}")
            news_text = "\n\n".join(news_lines)
            embed["fields"].append({
                "name": "📰 注目ニュース",
                "value": news_text[:1024],
                "inline": False,
            })

        # 予測
        predictions = report_data.get("predictions", [])
        if predictions:
            pred_text = "\n".join(
                f"{i+1}. {p['text']} (確信度{p.get('confidence', '?')}%)"
                for i, p in enumerate(predictions)
            )
            embed["fields"].append({
                "name": "🔮 予測",
                "value": pred_text[:1024],
                "inline": False,
            })

        # ひとこと
        comment = report_data.get("comment", "")
        if comment:
            embed["fields"].append({
                "name": "💡 ひとこと",
                "value": comment[:1024],
                "inline": False,
            })

        # レポートURL
        if report_url:
            embed["fields"].append({
                "name": "📄 フルレポート",
                "value": f"[ブラウザで見る]({report_url})",
                "inline": False,
            })

        payload = {"embeds": [embed]}

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info(f"Discord Embed送信成功 (ドメイン: {domain})")
            return True
        except requests.RequestException as e:
            logger.error(f"Discord Embed送信エラー: {e}")
            return False

    def send_report(self, report: str, report_url: str | None = None) -> bool:
        """レポートをEmbed要約+HTMLファイル添付で送信"""
        if not self.webhook_url:
            logger.warning("DISCORD_WEBHOOK_URL が設定されていません。通知スキップ。")
            return False

        # HTMLファイルを探す
        html_path = self._find_latest_html()

        # Markdownからサマリーを抽出してEmbed送信
        summary = self._extract_summary(report)
        today = datetime.now().strftime("%Y/%m/%d")

        embed = {
            "title": "🔮 MIRAI 未来予測レポート",
            "description": summary,
            "color": 0x38BDF8,
            "fields": [],
            "footer": {"text": f"MIRAI 未来予測 • {today}"},
            "timestamp": datetime.utcnow().isoformat(),
        }
        if report_url:
            embed["url"] = report_url

        # 短期予測の上位3つをフィールドに追加
        top_preds = self._extract_top_predictions(report)
        if top_preds:
            embed["fields"].append({
                "name": "⚡ 注目予測",
                "value": top_preds[:1024],
                "inline": False,
            })

        # リスクサマリー
        risks = self._extract_risks_brief(report)
        if risks:
            embed["fields"].append({
                "name": "🚨 主要リスク",
                "value": risks[:1024],
                "inline": True,
            })

        # 機会サマリー
        opps = self._extract_opportunities_brief(report)
        if opps:
            embed["fields"].append({
                "name": "✨ 主要機会",
                "value": opps[:1024],
                "inline": True,
            })

        # レポートURLフィールド
        if report_url:
            embed["fields"].append({
                "name": "📄 フルレポート",
                "value": f"[ブラウザで見る]({report_url})",
                "inline": False,
            })

        try:
            if html_path and html_path.exists():
                # Embed + HTMLファイル添付
                import json
                payload = {"embeds": [embed]}
                resp = requests.post(
                    self.webhook_url,
                    data={"payload_json": json.dumps(payload)},
                    files={"file": (html_path.name, html_path.read_bytes(), "text/html")},
                    timeout=30,
                )
            else:
                # HTMLがない場合はEmbedのみ
                payload = {"embeds": [embed]}
                resp = requests.post(self.webhook_url, json=payload, timeout=10)

            resp.raise_for_status()
            logger.info("Discord Embed+HTMLファイル送信成功")
            return True
        except requests.RequestException as e:
            logger.error(f"Discord送信エラー: {e}")
            # フォールバック: テキスト分割送信
            logger.info("フォールバック: テキスト分割送信を試みます")
            return self._send_report_text_fallback(report)

    def _send_report_text_fallback(self, report: str) -> bool:
        """フォールバック: 従来のテキスト分割送信"""
        chunks = self._split_message(report)
        logger.info(f"Discord送信(fallback): {len(chunks)}メッセージに分割")
        success = True
        for i, chunk in enumerate(chunks):
            if not self._send_chunk(chunk, i + 1, len(chunks)):
                success = False
        return success

    def _find_latest_html(self) -> Path | None:
        """reports/ 内の最新HTMLファイルを探す"""
        reports_dir = Path("reports")
        if not reports_dir.exists():
            return None
        html_files = sorted(reports_dir.glob("*.html"), key=lambda p: p.stat().st_mtime)
        return html_files[-1] if html_files else None

    def _extract_summary(self, report: str) -> str:
        """エグゼクティブサマリーの冒頭を抽出"""
        match = re.search(
            r"## エグゼクティブサマリー\s*\n+(.*?)(?=\n\*\*最も重要な予測|\n---|\n##)",
            report,
            re.DOTALL,
        )
        if match:
            text = match.group(1).strip()
            # 長すぎる場合は切り詰め
            if len(text) > 300:
                text = text[:297] + "..."
            return text
        return "最新の未来予測レポートです。添付のHTMLファイルで詳細をご確認ください。"

    def _extract_top_predictions(self, report: str) -> str:
        """確信度の高い予測を上位3件抽出"""
        pattern = re.compile(
            r"^\| *([A-Z]?\d+) *\| *(.*?) *\| *(テクノロジー|経済・マーケット|社会・文化) *\| *([\d.]+) *\|$",
            re.MULTILINE,
        )
        preds = []
        for m in pattern.finditer(report):
            conf = float(m.group(4))
            # 予測テキストを短縮
            text = m.group(2).strip()
            if len(text) > 80:
                text = text[:77] + "..."
            domain_emoji = {"テクノロジー": "💻", "経済・マーケット": "💰", "社会・文化": "🌍"}
            emoji = domain_emoji.get(m.group(3), "📌")
            preds.append((conf, f"{emoji} **{m.group(1)}** {text} (`{conf:.0%}`)"))

        # 確信度順にソート
        preds.sort(key=lambda x: x[0], reverse=True)
        return "\n".join(p[1] for p in preds[:5])

    def _extract_risks_brief(self, report: str) -> str:
        """リスク要因セクションからブリーフを抽出"""
        match = re.search(r"### リスク要因\s*\n+(.*?)(?=\n###|\n---|\n##)", report, re.DOTALL)
        if match:
            lines = [l.strip() for l in match.group(1).strip().split("\n") if l.strip().startswith(("- ", "* ", "1."))]
            brief = []
            for line in lines[:3]:
                text = re.sub(r"^[-*\d.]+\s*", "", line)
                # 太字タイトル部分だけ抽出
                bold = re.search(r"\*\*(.*?)\*\*", text)
                if bold:
                    brief.append(f"• {bold.group(1)}")
                elif len(text) > 60:
                    brief.append(f"• {text[:57]}...")
                else:
                    brief.append(f"• {text}")
            return "\n".join(brief)
        return ""

    def _extract_opportunities_brief(self, report: str) -> str:
        """機会セクションからブリーフを抽出"""
        match = re.search(r"### 機会\s*\n+(.*?)(?=\n---|\n##)", report, re.DOTALL)
        if match:
            lines = [l.strip() for l in match.group(1).strip().split("\n") if l.strip().startswith(("- ", "* ", "1."))]
            brief = []
            for line in lines[:3]:
                text = re.sub(r"^[-*\d.]+\s*", "", line)
                bold = re.search(r"\*\*(.*?)\*\*", text)
                if bold:
                    brief.append(f"• {bold.group(1)}")
                elif len(text) > 60:
                    brief.append(f"• {text[:57]}...")
                else:
                    brief.append(f"• {text}")
            return "\n".join(brief)
        return ""

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
