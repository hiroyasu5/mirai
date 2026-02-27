"""
Editor - 統合レポート生成エージェント
3ドメインの分析結果を統合し、Markdownレポートを生成する
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたは未来予測レポートの編集者です。
テクノロジー・経済・社会の3ドメインの分析結果を統合し、
包括的な未来予測レポートをMarkdownで生成します。

レポート構成:
1. エグゼクティブサマリー（全体の要約、最も重要な予測3つ）
2. 短期予測（3-6ヶ月）
3. 中期予測（1-2年）
4. 長期予測（5-10年）
5. ドメイン別分析
   - テクノロジー
   - 経済・マーケット
   - 社会・文化
6. クロスドメイン影響分析（ドメイン間の相互作用）
7. リスクと機会
8. 過去の予測レビュー（提供された場合）
9. 注目指標（今後ウォッチすべき指標・イベント）

ルール:
- 日本語で記述する
- 各予測には確信度(confidence)を明記する
- 具体的で検証可能な予測を優先する
- Markdownフォーマットで出力する（見出し、箇条書き、テーブルを適切に使う）
- レポートは1ファイルで完結させる"""


class Editor(BaseAgent):
    """3ドメインの分析を統合してMarkdownレポートを生成"""

    def __init__(self, config: dict):
        super().__init__(
            api_key=os.getenv("GEMINI_API_KEY"),
            model=config["models"]["editor"],
            system_prompt=SYSTEM_PROMPT,
        )
        self.output_dir = Path(config["report"]["output_dir"])
        self.template_path = Path("templates/report_template.md")

    def generate_report(
        self,
        analyses: dict[str, dict],
        past_predictions: list[dict] | None = None,
    ) -> str:
        """3ドメインの分析結果を統合してレポートを生成・保存"""
        logger.info("[Editor] レポート生成開始")

        template = self._load_template()
        prompt = self._build_prompt(analyses, past_predictions, template)
        report = self.call(prompt, max_tokens=8192)

        # レポート保存
        filepath = self._save_report(report)
        logger.info(f"[Editor] レポート保存: {filepath}")
        return report

    def _load_template(self) -> str:
        """レポートテンプレートを読み込む"""
        if self.template_path.exists():
            return self.template_path.read_text()
        return ""

    def _build_prompt(
        self,
        analyses: dict[str, dict],
        past_predictions: list[dict] | None,
        template: str,
    ) -> str:
        """エディタ用のプロンプトを構築"""
        parts = [
            f"現在日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}",
            "",
            "以下の3ドメインの分析結果を統合し、包括的な未来予測レポートをMarkdownで生成してください。",
            "",
        ]

        # 各ドメインの分析結果
        domain_labels = {
            "tech": "テクノロジー",
            "econ": "経済・マーケット",
            "social": "社会・文化",
        }
        for key, analysis in analyses.items():
            label = domain_labels.get(key, key)
            parts.append(f"## {label}分析結果")
            parts.append(json.dumps(analysis, ensure_ascii=False, indent=2))
            parts.append("")

        # 過去の予測
        if past_predictions:
            parts.append("## 過去の予測（精度レビュー用）")
            parts.append(json.dumps(past_predictions, ensure_ascii=False, indent=2))
            parts.append("")

        # テンプレート
        if template:
            parts.append("## レポートテンプレート（この構成に従ってください）")
            parts.append(template)
            parts.append("")

        return "\n".join(parts)

    def _save_report(self, report: str) -> Path:
        """レポートをファイルに保存"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = self.output_dir / f"{date_str}.md"

        # 同日に複数回実行された場合はサフィックス追加
        if filepath.exists():
            i = 2
            while True:
                filepath = self.output_dir / f"{date_str}-{i}.md"
                if not filepath.exists():
                    break
                i += 1

        filepath.write_text(report, encoding="utf-8")
        return filepath
