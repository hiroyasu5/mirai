"""
Publisher - HTMLレポートをGitHub Pagesに公開
docs/ にHTMLをコピーしてgit push する
"""

import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DOCS_DIR = Path("docs")
REPORTS_JSON = DOCS_DIR / "reports.json"
GITHUB_PAGES_BASE = "https://hiroyasu5.github.io/mirai"


class Publisher:
    """HTMLレポートをGitHub Pagesに公開"""

    def __init__(self):
        self.docs_dir = DOCS_DIR
        self.docs_dir.mkdir(exist_ok=True)

    def publish(self, html_path: Path) -> str | None:
        """HTMLレポートをdocs/にコピーしてgit pushし、公開URLを返す"""
        if not html_path.exists():
            logger.error(f"HTMLファイルが見つかりません: {html_path}")
            return None

        # docs/ にコピー
        dest = self.docs_dir / html_path.name
        shutil.copy2(html_path, dest)
        logger.info(f"HTMLをdocs/にコピー: {dest}")

        # reports.json を更新
        self._update_reports_json(html_path.name)

        # git add, commit, push
        if self._git_push(html_path.name):
            url = f"{GITHUB_PAGES_BASE}/{html_path.name}"
            logger.info(f"公開URL: {url}")
            return url
        return None

    def _update_reports_json(self, filename: str) -> None:
        """reports.json にエントリ追加"""
        reports = []
        if REPORTS_JSON.exists():
            try:
                reports = json.loads(REPORTS_JSON.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                reports = []

        # 日付をファイル名から抽出 (YYYY-MM-DD.html → YYYY-MM-DD)
        date_str = filename.replace(".html", "")

        # 既存エントリの重複チェック
        if not any(r["file"] == filename for r in reports):
            reports.append({
                "file": filename,
                "date": date_str,
                "mode": "フルレポート",
                "published_at": datetime.now().isoformat(),
            })

        REPORTS_JSON.write_text(
            json.dumps(reports, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _git_push(self, filename: str) -> bool:
        """docs/ の変更をcommit & push"""
        try:
            cmds = [
                ["git", "add", f"docs/{filename}", "docs/reports.json"],
                ["git", "commit", "-m", f"docs: publish report {filename}"],
                ["git", "push", "origin", "main"],
            ]
            for cmd in cmds:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode != 0:
                    # commit が空の場合は無視
                    if "nothing to commit" in result.stdout + result.stderr:
                        logger.info("変更なし、pushスキップ")
                        return True
                    logger.error(f"git error: {' '.join(cmd)}: {result.stderr}")
                    return False

            logger.info("git push 成功")
            return True
        except subprocess.TimeoutExpired:
            logger.error("git push タイムアウト")
            return False
        except Exception as e:
            logger.error(f"git push エラー: {e}")
            return False


def find_latest_html() -> Path | None:
    """reports/ 内の最新HTMLファイルを探す"""
    reports_dir = Path("reports")
    if not reports_dir.exists():
        return None
    html_files = sorted(reports_dir.glob("*.html"), key=lambda p: p.stat().st_mtime)
    return html_files[-1] if html_files else None
