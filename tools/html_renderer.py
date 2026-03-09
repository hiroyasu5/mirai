"""
HTML Renderer - MarkdownレポートをスタイリッシュなHTMLに変換
"""

import logging
import re
from pathlib import Path

import markdown

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path("templates/report_template.html")


def render_report_html(md_text: str, date_str: str) -> str:
    """MarkdownレポートをHTMLに変換して返す"""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    # Markdownからヘッダーとメタ情報を除去（HTMLテンプレート側で表示する）
    body = _strip_header(md_text)

    # 予測テーブルをカード形式に変換
    body = _convert_prediction_tables(body)

    # リスクと機会セクションを特別処理
    body = _convert_risk_opportunity(body)

    # 残りのMarkdownをHTMLに変換
    html_body = markdown.markdown(
        body,
        extensions=["tables", "fenced_code", "nl2br"],
    )

    # セクション見出しにアイコンを付与
    html_body = _add_section_icons(html_body)

    # セクションをdivで囲む
    html_body = _wrap_sections(html_body)

    # テンプレートに挿入
    html = template.replace("{{date}}", date_str)
    html = html.replace("{{content}}", html_body)

    return html


def _strip_header(md: str) -> str:
    """レポートの冒頭ヘッダー(タイトル・日時・対象期間)を除去"""
    lines = md.split("\n")
    start = 0
    for i, line in enumerate(lines):
        # 最初の "---" セパレータまでスキップ
        if line.strip() == "---":
            start = i + 1
            break
    return "\n".join(lines[start:])


def _convert_prediction_tables(md: str) -> str:
    """Markdownの予測テーブルをカード形式のHTMLに変換"""
    # テーブル行のパターン: | ID | 予測テキスト | ドメイン | 確信度 |
    # IDは "T1", "E2" 等のアルファベット+数字、または単純な数字
    table_pattern = re.compile(
        r"^\| *([A-Z]?\d+) *\| *(.*?) *\| *(テクノロジー|経済・マーケット|社会・文化) *\| *([\d.]+) *\|$",
        re.MULTILINE,
    )

    def _domain_class(domain: str) -> str:
        if "テクノロジー" in domain:
            return "tech"
        if "経済" in domain:
            return "econ"
        return "social"

    def _confidence_class(conf: float) -> str:
        if conf >= 0.75:
            return "high"
        if conf >= 0.5:
            return "mid"
        return "low"

    def _make_card(match: re.Match) -> str:
        pred_id = match.group(1)
        text = match.group(2).strip()
        domain = match.group(3).strip()
        confidence = float(match.group(4))
        dc = _domain_class(domain)
        cc = _confidence_class(confidence)
        pct = int(confidence * 100) if confidence <= 1 else int(confidence)
        display_conf = confidence if confidence <= 1 else confidence / 100

        return (
            f'<div class="pred-card domain-{dc}">'
            f'<div class="pred-header">'
            f'<span class="pred-id">{pred_id}</span>'
            f'<span class="pred-domain {dc}">{domain}</span>'
            f"</div>"
            f'<div class="pred-text">{text}</div>'
            f'<div class="confidence-bar">'
            f'<div class="confidence-track">'
            f'<div class="confidence-fill {cc}" style="width:{pct}%"></div>'
            f"</div>"
            f'<span class="confidence-label">{display_conf:.0%}</span>'
            f"</div>"
            f"</div>"
        )

    # テーブルヘッダー行を削除し、カード行をまとめてpred-gridに変換
    # まずテーブル行をカードに変換
    result = table_pattern.sub(_make_card, md)

    # テーブルヘッダー行を pred-grid 開始タグに変換
    result = re.sub(
        r"^\| *# *\| *予測 *\| *ドメイン *\| *確信度 *\|\n\|[-| ]+\|\n",
        '<div class="pred-grid">\n',
        result,
        flags=re.MULTILINE,
    )

    # pred-gridの閉じタグを挿入
    # カードブロック（</div>で終わる行）の後に空行が来るところにgrid閉じタグを追加
    lines = result.split("\n")
    new_lines = []
    in_grid = False
    for i, line in enumerate(lines):
        if '<div class="pred-grid">' in line:
            in_grid = True
        if in_grid and 'pred-card' not in line and '<div class="pred-grid">' not in line:
            # カードブロックが終わった
            new_lines.append("</div>")
            in_grid = False
        new_lines.append(line)
    if in_grid:
        new_lines.append("</div>")

    return "\n".join(new_lines)


def _convert_risk_opportunity(md: str) -> str:
    """リスクと機会セクションの特別処理は行わず、Markdown変換に任せる"""
    return md


def _add_section_icons(html: str) -> str:
    """セクション見出しにアイコンを追加"""
    icon_map = {
        "エグゼクティブサマリー": ("📋", "summary"),
        "前回予測との比較・変化分析": ("🔄", "evolution"),
        "短期予測（3-6ヶ月）": ("⚡", "short-term"),
        "中期予測（1-2年）": ("📈", "mid-term"),
        "長期予測（5-10年）": ("🔭", "long-term"),
        "ドメイン別分析": ("🔬", "domain"),
        "テクノロジー": ("💻", "tech"),
        "経済・マーケット": ("💰", "econ"),
        "社会・文化": ("🌍", "social"),
        "クロスドメイン影響分析": ("🔗", "cross"),
        "リスクと機会": ("⚖️", "risk-opp"),
        "リスク要因": ("🚨", "risk"),
        "機会": ("✨", "opp"),
        "過去の予測レビュー": ("📊", "review"),
        "注目指標": ("🎯", "indicators"),
    }

    for title, (icon, _cls) in icon_map.items():
        html = html.replace(
            f"<h2>{title}</h2>",
            f'<h2 class="section-title"><span class="icon">{icon}</span> {title}</h2>',
        )
        html = html.replace(
            f"<h3>{title}</h3>",
            f'<h3 class="section-title" style="font-size:1.1rem"><span class="icon">{icon}</span> {title}</h3>',
        )

    return html


def _wrap_sections(html: str) -> str:
    """h2の前にsectionのdivを挿入"""
    # h2タグの直前にsection区切りを入れる
    html = re.sub(
        r'(<h2 class="section-title">)',
        r'</div><div class="section">\1',
        html,
    )
    # 最初の余分な</div>を削除し、最後に閉じタグを追加
    if html.startswith("</div>"):
        html = html[len("</div>"):]
    html = '<div class="section">' + html + "</div>"

    # エグゼクティブサマリー直後の段落をsummary-boxで囲む
    html = re.sub(
        r'(📋</span> エグゼクティブサマリー</h2>)\s*<p>(.*?)</p>',
        r'\1<div class="summary-box"><p>\2</p></div>',
        html,
        flags=re.DOTALL,
    )

    return html
