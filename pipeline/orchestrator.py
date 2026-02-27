"""
Orchestrator - パイプライン統括
リサーチ → 分析 → レポート生成 → 通知の全フローを管理
"""

import logging
from datetime import datetime

from agents.researcher import Researcher
from agents.tech_analyst import TechAnalyst
from agents.econ_analyst import EconAnalyst
from agents.social_analyst import SocialAnalyst
from agents.editor import Editor
from pipeline.prediction_tracker import PredictionTracker
from tools.discord_notifier import DiscordNotifier

logger = logging.getLogger(__name__)


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
        return self.editor.generate_report(analyses, past if past else None)

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
        """Discord通知"""
        if not self.config["discord"]["enabled"]:
            logger.info("Discord通知はスキップされました（設定で無効）")
            return
        self.notifier.send_report(report)
