"""
Grok API ラッパー
xAI の grok-4 + x_search でXトレンドを収集する
"""

import json
import logging
import os
import re
from datetime import datetime

from xai_sdk import Client
from xai_sdk.chat import system, user
from xai_sdk.tools import x_search

logger = logging.getLogger(__name__)


class GrokSearcher:
    """Grok APIを使ってXからシグナルを収集"""

    def __init__(self, api_key: str, model: str = "grok-4"):
        self.client = Client(api_key=api_key)
        self.model = model

    def search(self, queries: list[str], topic_label: str,
               min_likes: int = 100, min_retweets: int = 20) -> dict:
        """複数クエリでX検索を実行し、シグナルを返す"""
        prompt = self._build_prompt(queries, topic_label, min_likes, min_retweets)
        raw = self._call_grok(prompt)
        signals = self._parse_response(raw, topic_label)
        return signals

    def _build_prompt(self, queries: list[str], topic_label: str,
                      min_likes: int, min_retweets: int) -> str:
        queries_text = "\n".join(f"- {q}" for q in queries)
        return f"""Search X right now for trending posts related to "{topic_label}".

Search queries to use:
{queries_text}

Screening criteria (strictly apply):
- English only
- Posted within last 48 hours
- Likes >= {min_likes}, Retweets >= {min_retweets}
- Real news, research, product announcements, or expert analysis only
- No promotional spam

Return a JSON object with this structure:
{{
  "topic": "{topic_label}",
  "collected_at": "{datetime.now().isoformat()}",
  "signals": [
    {{
      "author": "@username",
      "text": "tweet content",
      "url": "https://x.com/username/status/TWEET_ID",
      "likes": 500,
      "retweets": 80,
      "posted": "3 hours ago",
      "key_insight": "Brief English summary of why this matters"
    }}
  ]
}}

Find 3-5 high-quality signals. Output ONLY the JSON object."""

    def _call_grok(self, prompt: str) -> str:
        """Grok APIをx_searchツール付きで呼び出す"""
        logger.info("Grok x_search 開始...")
        chat = self.client.chat.create(
            model=self.model,
            tools=[x_search()],
        )
        chat.append(system(
            "You are an expert trend analyst. Search X for real trending posts "
            "and return structured JSON data. Always use x_search to find real posts."
        ))
        chat.append(user(prompt))

        content = ""
        for response, chunk in chat.stream():
            if chunk.content:
                content += chunk.content

        logger.info(f"Grok x_search 完了 ({len(content)}文字)")
        return content

    def _parse_response(self, content: str, topic_label: str) -> dict:
        """Grokレスポンスをパースしてシグナルdictに変換"""
        try:
            cleaned = re.sub(r"```(?:json)?", "", content).strip().rstrip("`").strip()
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                cleaned = match.group()
            data = json.loads(cleaned)

            # URLバリデーション
            for signal in data.get("signals", []):
                url = signal.get("url", "")
                if not re.match(r"https://(x\.com|twitter\.com)/\w+/status/\d{10,}", url):
                    signal["url"] = ""

            signal_count = len(data.get("signals", []))
            logger.info(f"[{topic_label}] {signal_count}件のシグナルを収集")
            return data

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"パースエラー [{topic_label}]: {e}\n内容: {content[:200]}")
            return {
                "topic": topic_label,
                "collected_at": datetime.now().isoformat(),
                "signals": [],
                "error": str(e),
            }
