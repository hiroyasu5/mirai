"""
MIRAI - 総合未来予測エージェントチーム
CLI エントリポイント

Usage:
    python main.py                      # フルパイプライン実行
    python main.py --mode research      # シグナル収集のみ
    python main.py --mode analyze       # キャッシュ済みシグナルを分析
    python main.py --mode track         # 過去予測の精度チェック
    python main.py --topic tech         # 特定ドメインのみ
    python main.py --no-discord         # Discord通知スキップ
    python main.py --verbose            # 詳細ログ出力
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from pipeline.orchestrator import Orchestrator


def load_config(config_path: str = "config/settings.yaml") -> dict:
    """設定ファイルを読み込む"""
    path = Path(config_path)
    if not path.exists():
        print(f"設定ファイルが見つかりません: {config_path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(verbose: bool = False) -> None:
    """ログ設定"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="MIRAI - 総合未来予測エージェントチーム",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "research", "analyze", "track"],
        default="full",
        help="実行モード (default: full)",
    )
    parser.add_argument(
        "--topic",
        choices=["tech", "econ", "social"],
        help="特定ドメインのみ実行",
    )
    parser.add_argument(
        "--no-discord",
        action="store_true",
        help="Discord通知をスキップ",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="詳細ログ出力",
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="設定ファイルパス",
    )

    args = parser.parse_args()

    # 初期化
    load_dotenv(override=True)
    setup_logging(args.verbose)
    config = load_config(args.config)

    if args.verbose:
        config["pipeline"]["verbose"] = True

    orchestrator = Orchestrator(config)
    use_discord = not args.no_discord

    try:
        if args.topic:
            # 特定ドメインのみ
            report = orchestrator.run_topic(args.topic, use_discord=use_discord)
            print(f"\nレポート生成完了（ドメイン: {args.topic}）")

        elif args.mode == "research":
            signals = orchestrator.run_research()
            print(f"\nシグナル収集完了: {len(signals)}ドメイン")

        elif args.mode == "analyze":
            analyses = orchestrator.run_analysis()
            report = orchestrator.run_report(analyses)
            if use_discord:
                orchestrator._notify(report)
            print("\n分析・レポート生成完了")

        elif args.mode == "track":
            result = orchestrator.run_track()
            stats = result["stats"]
            print(f"\n=== 予測精度レポート ===")
            print(f"総予測数: {stats['total']}")
            print(f"レビュー済み: {stats['reviewed']}")
            if stats["accuracy"] is not None:
                print(f"精度: {stats['accuracy']:.1%}")
            print(f"未検証: {result['pending_count']}")

        else:
            # フルパイプライン
            report = orchestrator.run_full(use_discord=use_discord)
            print("\nフルパイプライン完了。レポートは reports/ に保存されました。")

    except Exception as e:
        logging.error(f"エラー: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
