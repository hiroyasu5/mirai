"""
Gemini API + Google Search Grounding ラッパー
Google検索でトレンドシグナルを収集する
"""

import json
import logging
import os
import re
from datetime import datetime

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiSearcher:
    """Gemini API + Google Search Grounding でシグナルを収集"""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def search(self, queries: list[str], topic_label: str,
               min_likes: int = 100, min_retweets: int = 20) -> dict:
        """複数クエリでGoogle検索を実行し、シグナルを返す"""
        prompt = self._build_prompt(queries, topic_label)
        raw = self._call_gemini(prompt)
        signals = self._parse_response(raw, topic_label)
        return signals

    def _build_prompt(self, queries: list[str], topic_label: str) -> str:
        queries_text = "\n".join(f"- {q}" for q in queries)
        return f"""Search the web for the latest trending news and discussions related to "{topic_label}".

Search queries to use:
{queries_text}

Screening criteria (strictly apply):
- Posted or published within last 48 hours
- Real news, research, product announcements, or expert analysis only
- Prioritize high-impact, widely-discussed topics
- No promotional spam
- Include sources from X (Twitter), news sites, tech blogs, etc.

Return a JSON object with this structure:
{{
  "topic": "{topic_label}",
  "collected_at": "{datetime.now().isoformat()}",
  "signals": [
    {{
      "source": "source name or @username",
      "text": "summary of the signal",
      "url": "https://...",
      "key_insight": "Brief summary of why this matters for future predictions"
    }}
  ]
}}

Find 5-8 high-quality signals. Output ONLY the JSON object."""

    def _call_gemini(self, prompt: str) -> str:
        """Gemini APIをGoogle Search Grounding付きで呼び出す"""
        logger.info("Gemini Google Search 開始...")

        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[google_search_tool],
                system_instruction=(
                    "You are an expert trend analyst. Use Google Search to find "
                    "the latest real trending topics, news, and discussions. "
                    "Return structured JSON data with verified, real information."
                ),
                max_output_tokens=8192,
            ),
        )
        content = response.text
        logger.info(f"Gemini Google Search 完了 ({len(content)}文字)")
        return content

    def _parse_response(self, content: str, topic_label: str) -> dict:
        """レスポンスをパースしてシグナルdictに変換"""
        try:
            cleaned = re.sub(r"```(?:json)?", "", content).strip().rstrip("`").strip()
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                cleaned = match.group()
            data = json.loads(cleaned)

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
