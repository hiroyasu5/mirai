"""
Researcher - Grok x_search によるシグナル収集エージェント
各ドメイン(tech/econ/social)のXトレンドを収集する
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from tools.web_search import GrokSearcher

logger = logging.getLogger(__name__)


class Researcher:
    """Grok APIでXトレンドを収集するリサーチャー"""

    def __init__(self, config: dict):
        self.config = config
        self.searcher = GrokSearcher(
            api_key=os.getenv("GROK_API_KEY"),
            model=config["models"]["researcher"],
        )
        self.research_config = config["research"]
        self.cache_dir = Path(config["pipeline"].get("cache_dir", "data/cache"))

    def collect_all(self) -> dict[str, dict]:
        """全ドメインのシグナルを収集"""
        logger.info("=== シグナル収集開始 ===")
        results = {}
        for topic_key, topic_conf in self.research_config["topics"].items():
            results[topic_key] = self.collect_topic(topic_key, topic_conf)
        logger.info(f"=== シグナル収集完了: {len(results)}ドメイン ===")
        return results

    def collect_topic(self, topic_key: str, topic_conf: dict) -> dict:
        """特定ドメインのシグナルを収集"""
        label = topic_conf["label"]
        queries = topic_conf["queries"]
        logger.info(f"[{label}] シグナル収集中...")

        signals = self.searcher.search(
            queries=queries,
            topic_label=label,
            min_likes=self.research_config.get("min_likes", 100),
            min_retweets=self.research_config.get("min_retweets", 20),
        )

        # キャッシュ保存
        if self.config["pipeline"].get("cache_signals", True):
            self._save_cache(topic_key, signals)

        return signals

    def load_cached(self) -> dict[str, dict] | None:
        """キャッシュ済みシグナルを読み込む"""
        results = {}
        for topic_key in self.research_config["topics"]:
            cache_file = self.cache_dir / f"{topic_key}_signals.json"
            if not cache_file.exists():
                logger.warning(f"キャッシュなし: {cache_file}")
                return None
            with open(cache_file) as f:
                results[topic_key] = json.load(f)
        logger.info(f"キャッシュから{len(results)}ドメインのシグナルを読み込みました")
        return results

    def _save_cache(self, topic_key: str, signals: dict) -> None:
        """シグナルをキャッシュファイルに保存"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"{topic_key}_signals.json"
        with open(cache_file, "w") as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        logger.info(f"キャッシュ保存: {cache_file}")
