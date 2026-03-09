"""
Daily HTML Renderer - dailyレポート(JSON)をスタイリッシュなHTMLに変換
"""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DOMAIN_THEMES = {
    "tech": {"color": "#3b82f6", "bg": "rgba(59,130,246,0.1)", "emoji": "💻", "label": "テクノロジー"},
    "econ": {"color": "#f59e0b", "bg": "rgba(245,158,11,0.1)", "emoji": "💰", "label": "経済・マーケット"},
    "social": {"color": "#10b981", "bg": "rgba(16,185,129,0.1)", "emoji": "🌍", "label": "社会・文化"},
}


def render_daily_html(domain: str, report_data: dict) -> str:
    """dailyレポートJSONをHTMLに変換"""
    theme = DOMAIN_THEMES.get(domain, DOMAIN_THEMES["tech"])
    date_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    title = report_data.get("title", f"今日の{theme['label']}予測")
    summary = report_data.get("summary", "")
    comment = report_data.get("comment", "")

    # ニュースカード
    news_html = ""
    for item in report_data.get("news", []):
        headline = item.get("headline", "")
        detail = item.get("detail", "")
        url = item.get("url", "")
        link = f'<a href="{url}" target="_blank" rel="noopener">{headline}</a>' if url else headline
        news_html += f"""
        <div class="news-card">
          <div class="news-headline">{link}</div>
          <div class="news-detail">{detail}</div>
        </div>"""

    # 予測カード
    preds_html = ""
    for i, pred in enumerate(report_data.get("predictions", []), 1):
        text = pred.get("text", "")
        conf = pred.get("confidence", 0)
        conf_class = "high" if conf >= 75 else "mid" if conf >= 50 else "low"
        preds_html += f"""
        <div class="pred-card">
          <div class="pred-num">{i}</div>
          <div class="pred-body">
            <div class="pred-text">{text}</div>
            <div class="confidence-bar">
              <div class="confidence-track">
                <div class="confidence-fill {conf_class}" style="width:{conf}%"></div>
              </div>
              <span class="confidence-label">{conf}%</span>
            </div>
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --bg: #0f172a;
    --surface: #1e293b;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --accent: {theme['color']};
    --border: #475569;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', 'Hiragino Sans', 'Noto Sans JP', sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.7;
  }}
  .header {{
    background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 50%, #1a1a2e 100%);
    padding: 2.5rem 2rem; text-align: center;
    border-bottom: 3px solid var(--accent);
  }}
  .header h1 {{ font-size: 1.8rem; color: #fff; }}
  .header .meta {{ color: var(--text-muted); margin-top: 0.5rem; font-size: 0.9rem; }}
  .container {{ max-width: 800px; margin: 0 auto; padding: 2rem 1.5rem; }}
  .section {{ margin-bottom: 2rem; }}
  .section-title {{
    font-size: 1.2rem; font-weight: 700; color: var(--accent);
    margin-bottom: 1rem; padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--border);
  }}
  .summary {{
    background: var(--surface); border: 1px solid var(--border);
    border-left: 4px solid var(--accent); border-radius: 10px;
    padding: 1.2rem 1.5rem; font-size: 0.95rem; line-height: 1.8;
  }}
  .news-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
  }}
  .news-headline {{ font-weight: 600; margin-bottom: 0.3rem; }}
  .news-headline a {{ color: var(--accent); text-decoration: none; }}
  .news-headline a:hover {{ text-decoration: underline; }}
  .news-detail {{ font-size: 0.88rem; color: var(--text-muted); }}
  .pred-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 1.2rem 1.5rem; margin-bottom: 0.8rem;
    display: flex; gap: 1rem; align-items: flex-start;
  }}
  .pred-num {{
    background: var(--accent); color: var(--bg); font-weight: 800;
    font-size: 1.1rem; min-width: 2.2rem; height: 2.2rem;
    border-radius: 50%; display: flex; align-items: center;
    justify-content: center; flex-shrink: 0;
  }}
  .pred-body {{ flex: 1; }}
  .pred-text {{ font-size: 0.92rem; margin-bottom: 0.6rem; }}
  .confidence-bar {{ display: flex; align-items: center; gap: 0.8rem; }}
  .confidence-track {{
    flex: 1; height: 8px; background: #334155;
    border-radius: 4px; overflow: hidden;
  }}
  .confidence-fill {{ height: 100%; border-radius: 4px; }}
  .confidence-fill.high {{ background: linear-gradient(90deg, #22c55e, #4ade80); }}
  .confidence-fill.mid {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}
  .confidence-fill.low {{ background: linear-gradient(90deg, #ef4444, #f87171); }}
  .confidence-label {{ font-size: 0.85rem; font-weight: 700; min-width: 3rem; text-align: right; }}
  .comment {{
    background: {theme['bg']}; border: 1px solid var(--border);
    border-radius: 10px; padding: 1.2rem 1.5rem;
    font-size: 0.92rem; color: var(--text-muted);
  }}
  .footer {{
    text-align: center; padding: 2rem; color: var(--text-muted);
    font-size: 0.8rem; border-top: 1px solid var(--border); margin-top: 2rem;
  }}
</style>
</head>
<body>
<div class="header">
  <h1>{theme['emoji']} {title}</h1>
  <div class="meta">📅 {date_str}</div>
</div>
<div class="container">
  <div class="section">
    <div class="summary">{summary}</div>
  </div>
  <div class="section">
    <div class="section-title">📰 注目ニュース</div>
    {news_html}
  </div>
  <div class="section">
    <div class="section-title">🔮 予測</div>
    {preds_html}
  </div>
  {"<div class='section'><div class='section-title'>💡 ひとこと</div><div class='comment'>" + comment + "</div></div>" if comment else ""}
</div>
<div class="footer">
  🤖 MIRAI（未来予測エージェントチーム）により自動生成
</div>
</body>
</html>"""


def save_daily_html(domain: str, report_data: dict) -> Path:
    """dailyレポートをHTMLとして保存"""
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = reports_dir / f"{date_str}.html"
    if filepath.exists():
        i = 2
        while True:
            filepath = reports_dir / f"{date_str}-{i}.html"
            if not filepath.exists():
                break
            i += 1

    html = render_daily_html(domain, report_data)
    filepath.write_text(html, encoding="utf-8")
    logger.info(f"Daily HTMLレポート保存: {filepath}")
    return filepath
