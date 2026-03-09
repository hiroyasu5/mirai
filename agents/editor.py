"""
Editor - 統合レポート生成エージェント
3ドメインの分析結果を統合し、Markdownレポートを生成する
dailyモードでは1ドメイン特化の短いJSON形式レポートも生成可能
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from agents.base import BaseAgent
from tools.html_renderer import render_report_html

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたは未来予測レポートの編集者です。
テクノロジー・経済・社会の3ドメインの分析結果を統合し、
包括的な未来予測レポートをMarkdownで生成します。

レポート構成:
1. エグゼクティブサマリー（全体の要約、最も重要な予測3つ）
2. 前回予測との比較・変化分析（前回レポートが提供された場合は必須）
   - 前回の主要予測と今回の状況の対比
   - 予測の的中・外れ・進行中の分類
   - 新たに浮上したトレンドや予想外の変化
   - 確信度の変動とその理由
3. 短期予測（3-6ヶ月）
4. 中期予測（1-2年）
5. 長期予測（5-10年）
6. ドメイン別分析
   - テクノロジー
   - 経済・マーケット
   - 社会・文化
7. クロスドメイン影響分析（ドメイン間の相互作用）
8. リスクと機会
9. 過去の予測レビュー（提供された場合）
10. 注目指標（今後ウォッチすべき指標・イベント）

ルール:
- 日本語で記述する
- 各予測には確信度(confidence)を明記する
- 具体的で検証可能な予測を優先する
- Markdownフォーマットで出力する（見出し、箇条書き、テーブルを適切に使う）
- レポートは1ファイルで完結させる
- 前回レポートが提供された場合、必ず「前回予測との比較・変化分析」セクションを含めること
- 前回と今回で予測が変わった場合は、その理由を明確に説明すること"""

DAILY_SYSTEM_PROMPT = """あなたは未来予測レポートの編集者です。
1つのドメインに特化した、短く読みやすいレポートをJSON形式で生成します。

出力は必ず以下のJSON構造のみを返してください（Markdownや説明文は不要）:
{
  "title": "今日の○○予測",
  "summary": "2-3行の要約文。今日の最も重要なポイントを簡潔に。",
  "news": [
    {
      "headline": "注目ニュースの見出し",
      "detail": "1-2文の詳細説明",
      "url": "情報元のURL"
    }
  ],
  "predictions": [
    {
      "text": "具体的な予測内容",
      "confidence": 85
    },
    {
      "text": "具体的な予測内容",
      "confidence": 80
    },
    {
      "text": "具体的な予測内容",
      "confidence": 75
    }
  ],
  "comment": "1-2文の編集者コメント。読者への一言。"
}

ルール:
- 日本語で記述する
- newsは5個（分析結果のシグナルからURLを含めて抽出すること）
- predictionsは必ず3つ
- 各予測のconfidenceは0-100の整数
- summaryは簡潔に2-3行
- commentは親しみやすいトーンで
- newsの各項目には必ず情報元のurlを含めること（分析結果のsignalsに含まれるURLを使用）
- JSON以外の文字列を出力しないこと"""


DOMAIN_LABELS = {
    "tech": "テクノロジー",
    "econ": "経済・マーケット",
    "social": "社会・文化",
}


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

    def generate_daily_report(self, domain: str, analysis: dict) -> dict:
        """1ドメイン特化の短いレポートをJSON形式で生成"""
        logger.info(f"[Editor] dailyレポート生成開始 (ドメイン: {domain})")

        # dailyモード用のシステムプロンプトに一時切り替え
        original_prompt = self.system_prompt
        self.system_prompt = DAILY_SYSTEM_PROMPT

        try:
            label = DOMAIN_LABELS.get(domain, domain)
            prompt = (
                f"現在日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}\n\n"
                f"以下の「{label}」ドメインの分析結果から、短く読みやすいレポートをJSON形式で生成してください。\n\n"
                f"## {label}分析結果\n"
                f"{json.dumps(analysis, ensure_ascii=False, indent=2)}"
            )
            result = self.call_json(prompt, max_tokens=4096)
            logger.info(f"[Editor] dailyレポート生成完了 (ドメイン: {domain})")
            return result
        finally:
            self.system_prompt = original_prompt

    def generate_report(
        self,
        analyses: dict[str, dict],
        past_predictions: list[dict] | None = None,
        previous_report: str | None = None,
    ) -> str:
        """3ドメインの分析結果を統合してレポートを生成・保存"""
        logger.info("[Editor] レポート生成開始")

        template = self._load_template()
        prompt = self._build_prompt(analyses, past_predictions, template, previous_report)
        report = self.call(prompt, max_tokens=8192)

        # レポート保存（Markdown + HTML）
        filepath = self._save_report(report)
        html_path = self._save_html_report(report)
        logger.info(f"[Editor] レポート保存: {filepath}")
        logger.info(f"[Editor] HTMLレポート保存: {html_path}")
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
        previous_report: str | None = None,
    ) -> str:
        """エディタ用のプロンプトを構築"""
        parts = [
            f"現在日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}",
            "",
            "以下の3ドメインの分析結果を統合し、包括的な未来予測レポートをMarkdownで生成してください。",
            "",
        ]

        # 前回レポート（比較用）
        if previous_report:
            parts.append("## 前回のレポート（比較・変化分析用）")
            parts.append("以下は前回生成されたレポートです。今回のレポートでは、前回の予測と現在の状況を比較し、")
            parts.append("「前回予測との比較・変化分析」セクションで以下を明確に記述してください：")
            parts.append("- 前回の主要予測がどう推移したか（的中/外れ/進行中）")
            parts.append("- 新たに浮上したトレンドや予想外の変化")
            parts.append("- 確信度が変動した予測とその理由")
            parts.append("")
            parts.append(previous_report)
            parts.append("")

        # 各ドメインの分析結果
        for key, analysis in analyses.items():
            label = DOMAIN_LABELS.get(key, key)
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

    def _save_html_report(self, report: str) -> Path:
        """レポートをHTMLファイルに保存"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = self.output_dir / f"{date_str}.html"

        # 同日に複数回実行された場合はサフィックス追加
        if filepath.exists():
            i = 2
            while True:
                filepath = self.output_dir / f"{date_str}-{i}.html"
                if not filepath.exists():
                    break
                i += 1

        display_date = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        html = render_report_html(report, display_date)
        filepath.write_text(html, encoding="utf-8")
        return filepath
