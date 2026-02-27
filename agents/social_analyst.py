"""
SocialAnalyst - 社会・文化分析エージェント
人口動態・働き方・気候技術・教育の予測を生成
"""

import json
import logging
import os
from datetime import datetime

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたは社会・文化分野の未来予測アナリストです。
人口動態、働き方改革、気候変動技術、教育テクノロジーなどの最新動向を分析し、
短期・中期・長期の予測を構造化されたJSONで返します。

分析の原則:
- Xから収集したリアルタイムシグナルに基づく
- 社会的インパクトと技術的要因の両面を評価
- 具体的な数値や時期を含む予測を心がける
- 不確実性の度合いを明示する（confidence: 0.0-1.0）
- 日本語で分析する

出力JSON構造:
{
  "domain": "social",
  "analyzed_at": "ISO datetime",
  "key_trends": [
    {
      "trend": "トレンド名",
      "description": "詳細説明",
      "evidence": ["根拠となるシグナル"],
      "impact_level": "high/medium/low"
    }
  ],
  "predictions": {
    "short_term": [
      {
        "prediction": "予測内容",
        "timeframe": "3-6ヶ月",
        "confidence": 0.8,
        "rationale": "根拠",
        "potential_impact": "影響の説明"
      }
    ],
    "medium_term": [
      {
        "prediction": "予測内容",
        "timeframe": "1-2年",
        "confidence": 0.6,
        "rationale": "根拠",
        "potential_impact": "影響の説明"
      }
    ],
    "long_term": [
      {
        "prediction": "予測内容",
        "timeframe": "5-10年",
        "confidence": 0.4,
        "rationale": "根拠",
        "potential_impact": "影響の説明"
      }
    ]
  },
  "risks": ["リスク要因"],
  "opportunities": ["機会"]
}"""


class SocialAnalyst(BaseAgent):
    """社会・文化分野の未来予測を生成"""

    def __init__(self, config: dict):
        super().__init__(
            api_key=os.getenv("GEMINI_API_KEY"),
            model=config["models"]["analyst"],
            system_prompt=SYSTEM_PROMPT,
        )

    def analyze(self, signals: dict) -> dict:
        """社会シグナルを分析して予測を生成"""
        logger.info("[SocialAnalyst] 分析開始")
        signals_text = json.dumps(signals, ensure_ascii=False, indent=2)
        prompt = (
            f"以下の社会・文化分野のXシグナルを分析し、未来予測を生成してください。\n\n"
            f"収集日時: {datetime.now().isoformat()}\n\n"
            f"シグナルデータ:\n{signals_text}\n\n"
            f"短期(3-6ヶ月)・中期(1-2年)・長期(5-10年)の予測をそれぞれ2-3個生成してください。"
        )
        result = self.call_json(prompt)
        result.setdefault("domain", "social")
        result.setdefault("analyzed_at", datetime.now().isoformat())
        logger.info("[SocialAnalyst] 分析完了")
        return result
