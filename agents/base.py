"""
BaseAgent - Claude API ラッパー
全アナリスト・エディタの基底クラス
"""

import json
import logging
import re
from typing import Any

import anthropic

logger = logging.getLogger(__name__)


class BaseAgent:
    """Claude APIを使用するエージェントの基底クラス"""

    def __init__(self, api_key: str, model: str, system_prompt: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt

    def call(self, user_message: str, max_tokens: int = 4096) -> str:
        """Claude APIを呼び出してテキスト応答を取得"""
        logger.info(f"[{self.__class__.__name__}] API呼び出し開始")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        text = response.content[0].text
        logger.info(f"[{self.__class__.__name__}] API呼び出し完了 ({len(text)}文字)")
        return text

    def call_json(self, user_message: str, max_tokens: int = 4096) -> dict[str, Any]:
        """Claude APIを呼び出してJSON応答をパース"""
        raw = self.call(user_message, max_tokens)
        return self._parse_json(raw)

    def _parse_json(self, text: str) -> dict[str, Any]:
        """テキストからJSONを抽出してパース"""
        # コードブロックを除去
        cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        # JSON部分を抽出
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSONパースエラー: {e}\n内容: {text[:300]}")
            return {"error": str(e), "raw": text[:500]}
