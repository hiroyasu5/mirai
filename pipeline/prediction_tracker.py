"""
PredictionTracker - 過去予測の精度追跡
predictions.json に予測を記録し、過去の予測を検索する
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PredictionTracker:
    """予測の記録と精度追跡"""

    def __init__(self, predictions_file: str = "data/predictions.json"):
        self.filepath = Path(predictions_file)
        self._ensure_file()

    def _ensure_file(self) -> None:
        """predictions.json がなければ作成"""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self.filepath.exists():
            self.filepath.write_text("[]", encoding="utf-8")

    def load_all(self) -> list[dict]:
        """全予測を読み込む"""
        with open(self.filepath, encoding="utf-8") as f:
            return json.load(f)

    def save_predictions(self, analyses: dict[str, dict]) -> None:
        """分析結果から予測を抽出して記録"""
        existing = self.load_all()
        timestamp = datetime.now().isoformat()

        for domain_key, analysis in analyses.items():
            predictions = analysis.get("predictions", {})
            for timeframe, pred_list in predictions.items():
                if not isinstance(pred_list, list):
                    continue
                for pred in pred_list:
                    entry = {
                        "id": f"{timestamp}_{domain_key}_{len(existing)}",
                        "recorded_at": timestamp,
                        "domain": analysis.get("domain", domain_key),
                        "timeframe": timeframe,
                        "prediction": pred.get("prediction", ""),
                        "confidence": pred.get("confidence", 0.0),
                        "rationale": pred.get("rationale", ""),
                        "status": "pending",  # pending / correct / incorrect / partially_correct
                        "review_notes": "",
                    }
                    existing.append(entry)

        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        new_count = len(existing)
        logger.info(f"予測記録完了: 合計{new_count}件")

    def get_past_predictions(self, limit: int = 20) -> list[dict]:
        """過去の予測を取得（レビュー用）"""
        all_preds = self.load_all()
        if not all_preds:
            return []
        # 最新のものから返す
        return all_preds[-limit:]

    def get_pending_predictions(self) -> list[dict]:
        """未検証の予測を取得"""
        all_preds = self.load_all()
        return [p for p in all_preds if p.get("status") == "pending"]

    def update_prediction(self, pred_id: str, status: str, notes: str = "") -> bool:
        """予測のステータスを更新"""
        all_preds = self.load_all()
        for pred in all_preds:
            if pred.get("id") == pred_id:
                pred["status"] = status
                pred["review_notes"] = notes
                pred["reviewed_at"] = datetime.now().isoformat()
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(all_preds, f, ensure_ascii=False, indent=2)
                return True
        return False

    def get_accuracy_stats(self) -> dict:
        """予測精度の統計を計算"""
        all_preds = self.load_all()
        reviewed = [p for p in all_preds if p.get("status") != "pending"]
        if not reviewed:
            return {"total": len(all_preds), "reviewed": 0, "accuracy": None}

        correct = len([p for p in reviewed if p["status"] == "correct"])
        partial = len([p for p in reviewed if p["status"] == "partially_correct"])
        incorrect = len([p for p in reviewed if p["status"] == "incorrect"])

        return {
            "total": len(all_preds),
            "reviewed": len(reviewed),
            "correct": correct,
            "partially_correct": partial,
            "incorrect": incorrect,
            "accuracy": (correct + partial * 0.5) / len(reviewed) if reviewed else None,
        }
