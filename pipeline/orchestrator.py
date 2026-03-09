"""
Orchestrator - パイプライン統括
リサーチ → 分析 → レポート生成 → 通知の全フローを管理
"""

import logging
from datetime import datetime
from pathlib import Path

from agents.researcher import Researcher
from agents.tech_analyst import TechAnalyst
from agents.econ_analyst import EconAnalyst
from agents.social_analyst import SocialAnalyst
from agents.editor import Editor
from pipeline.prediction_tracker import PredictionTracker
from tools.discord_notifier import DiscordNotifier
from tools.daily_html_renderer import save_daily_html
from tools.publisher import Publisher, find_latest_html

logger = logging.getLogger(__name__)


DOMAIN_ROTATION = ["tech", "econ", "social"]
LAST_TOPIC_FILE = Path("data/last_topic.txt")


class Orchestrator:
    """パイプライン全体を統括"""

    def __init__(self, config: dict):
        self.config = config
        self.researcher = Researcher(config)
        self.tech_analyst = TechAnalyst(config)
        self.econ_analyst = EconAnalyst(config)
        self.social_analyst = SocialAnalyst(config)
        self.editor = Editor(config)
        self.tracker = PredictionTracker(config["report"]["predictions_file"])
        self.notifier = DiscordNotifier(config)
        self.publisher = Publisher()

    def _get_next_domain(self) -> str:
        """ローテーションで次のドメインを決定"""
        if LAST_TOPIC_FILE.exists():
            last = LAST_TOPIC_FILE.read_text(encoding="utf-8").strip()
            try:
                idx = DOMAIN_ROTATION.index(last)
                next_domain = DOMAIN_ROTATION[(idx + 1) % len(DOMAIN_ROTATION)]
            except ValueError:
                next_domain = DOMAIN_ROTATION[0]
        else:
            next_domain = DOMAIN_ROTATION[0]

        # 次回のために記録
        LAST_TOPIC_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_TOPIC_FILE.write_text(next_domain, encoding="utf-8")
        return next_domain

    def run_daily(self, use_discord: bool = True) -> dict:
        """dailyモード: 1ドメインだけ収集→分析→Embed通知"""
        domain = self._get_next_domain()
        logger.info("=" * 60)
        logger.info(f"MIRAI dailyパイプライン開始 (ドメイン: {domain})")
        logger.info("=" * 60)

        # Step 1: 該当ドメインのシグナル収集
        topics = self.config["research"]["topics"]
        signals = {domain: self.researcher.collect_topic(domain, topics[domain])}

        # Step 2: 分析
        analyst_map = {
            "tech": self.tech_analyst,
            "econ": self.econ_analyst,
            "social": self.social_analyst,
        }
        analysis = analyst_map[domain].analyze(signals[domain])
        self.tracker.save_predictions({domain: analysis})

        # Step 3: dailyレポート生成（JSON形式）
        report_data = self.editor.generate_daily_report(domain, analysis)

        # Step 4: Discord Embed通知
        if use_discord:
            self._notify_daily(domain, report_data)

        logger.info("=" * 60)
        logger.info(f"MIRAI dailyパイプライン完了 (ドメイン: {domain})")
        logger.info("=" * 60)
        return {"domain": domain, "report": report_data}

    def _notify_daily(self, domain: str, report_data: dict) -> None:
        """daily用: HTML生成→公開→Discord Embed通知"""
        # dailyレポートのHTML生成・公開
        html_path = save_daily_html(domain, report_data)
        report_url = self.publisher.publish(html_path)
        if report_url:
            logger.info(f"dailyレポート公開URL: {report_url}")

        if not self.config["discord"]["enabled"]:
            logger.info("Discord通知はスキップされました（設定で無効）")
            return
        self.notifier.send_daily_embed(domain, report_data, report_url=report_url)

    def run_full(self, use_discord: bool = True) -> str:
        """フルパイプライン: 収集 → 分析 → レポート → 通知"""
        logger.info("=" * 60)
        logger.info("MIRAI フルパイプライン開始")
        logger.info("=" * 60)

        # Step 1: シグナル収集
        signals = self.run_research()

        # Step 2: 分析
        analyses = self.run_analysis(signals)

        # Step 3: レポート生成
        report = self.run_report(analyses)

        # Step 4: Discord通知
        if use_discord:
            self._notify(report)

        logger.info("=" * 60)
        logger.info("MIRAI フルパイプライン完了")
        logger.info("=" * 60)
        return report

    def run_research(self) -> dict[str, dict]:
        """シグナル収集のみ"""
        logger.info("--- Phase: シグナル収集 ---")
        return self.researcher.collect_all()

    def run_analysis(self, signals: dict[str, dict] | None = None) -> dict[str, dict]:
        """分析のみ（シグナルがなければキャッシュから読み込む）"""
        logger.info("--- Phase: 分析 ---")

        if signals is None:
            signals = self.researcher.load_cached()
            if signals is None:
                raise RuntimeError("シグナルキャッシュが見つかりません。先に --mode research を実行してください。")

        analyses = {}

        # 各ドメインの分析
        if "tech" in signals:
            analyses["tech"] = self.tech_analyst.analyze(signals["tech"])
        if "econ" in signals:
            analyses["econ"] = self.econ_analyst.analyze(signals["econ"])
        if "social" in signals:
            analyses["social"] = self.social_analyst.analyze(signals["social"])

        # 予測を記録
        self.tracker.save_predictions(analyses)

        return analyses

    def run_report(self, analyses: dict[str, dict]) -> str:
        """レポート生成のみ"""
        logger.info("--- Phase: レポート生成 ---")
        past = self.tracker.get_past_predictions()
        previous_report = self._load_previous_report()
        return self.editor.generate_report(
            analyses,
            past if past else None,
            previous_report=previous_report,
        )

    def _load_previous_report(self) -> str | None:
        """reports/ 内の最新レポートを読み込む"""
        reports_dir = Path(self.config["report"]["output_dir"])
        if not reports_dir.exists():
            return None

        report_files = sorted(reports_dir.glob("*.md"), key=lambda p: p.stat().st_mtime)
        if not report_files:
            return None

        latest = report_files[-1]
        logger.info(f"前回レポート読み込み: {latest.name}")
        return latest.read_text(encoding="utf-8")

    def run_track(self) -> dict:
        """過去予測の精度チェック"""
        logger.info("--- Phase: 予測精度チェック ---")
        stats = self.tracker.get_accuracy_stats()
        pending = self.tracker.get_pending_predictions()

        logger.info(f"総予測数: {stats['total']}")
        logger.info(f"レビュー済み: {stats['reviewed']}")
        if stats["accuracy"] is not None:
            logger.info(f"精度: {stats['accuracy']:.1%}")
        logger.info(f"未検証: {len(pending)}")

        return {"stats": stats, "pending_count": len(pending)}

    def run_topic(self, topic: str, use_discord: bool = True) -> str:
        """特定ドメインのみ実行"""
        logger.info(f"--- 単一ドメイン実行: {topic} ---")

        topics = self.config["research"]["topics"]
        if topic not in topics:
            raise ValueError(f"不明なドメイン: {topic} (選択肢: {list(topics.keys())})")

        # 該当ドメインのみ収集
        signals = {topic: self.researcher.collect_topic(topic, topics[topic])}

        # 該当ドメインのみ分析
        analyst_map = {
            "tech": self.tech_analyst,
            "econ": self.econ_analyst,
            "social": self.social_analyst,
        }
        analyst = analyst_map[topic]
        analyses = {topic: analyst.analyze(signals[topic])}

        # 予測記録
        self.tracker.save_predictions(analyses)

        # レポート生成
        report = self.run_report(analyses)

        if use_discord:
            self._notify(report)

        return report

    def _notify(self, report: str) -> None:
        """GitHub Pagesに公開してからDiscord通知"""
        # HTMLをGitHub Pagesに公開
        html_path = find_latest_html()
        report_url = None
        if html_path:
            report_url = self.publisher.publish(html_path)
            if report_url:
                logger.info(f"レポート公開URL: {report_url}")

        if not self.config["discord"]["enabled"]:
            logger.info("Discord通知はスキップされました（設定で無効）")
            return
        self.notifier.send_report(report, report_url=report_url)
