"""
rpi_engine.py - Review-Priority Index (RPI) & Dynamic Routing Engine

Implements the tri-factor RPI formulation:
RPI = w1 * U_calib(x) + w2 * S(c) + w3 * (1 - F_exp(H, T, x))
"""

import os, sys
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

try:
    from src.severity import compute_severity
    from src.faithfulness_guard import FaithfulnessGuard
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.severity import compute_severity
    from src.faithfulness_guard import FaithfulnessGuard


class RPIEngine:
    """
    Review-Priority Index Engine.
    Ranks incoming inspection frames and routes high-risk calls to human operators.
    """

    def __init__(
        self,
        w1: float = 0.35,
        w2: float = 0.35,
        w3: float = 0.30,
        routing_target_pct: float = 0.15
    ):
        # Normalize weights to sum to 1.0
        total_w = w1 + w2 + w3
        self.w1 = w1 / total_w
        self.w2 = w2 / total_w
        self.w3 = w3 / total_w
        self.routing_target_pct = routing_target_pct
        self.guard = FaithfulnessGuard()

    def compute_rpi(
        self,
        prediction: Dict[str, Any],
        ground_truth_meta: Dict[str, Any],
        temperature: float = 1.0
    ) -> Dict[str, Any]:
        """
        Computes RPI for a single inspection frame.
        """
        raw_conf = prediction.get("confidence", 0.80)
        pred_label = prediction.get("predicted_label", "normal")
        area_ratio = ground_truth_meta.get("area_ratio", 0.0)

        # 1. Calibrated Uncertainty U_calib(x)
        # Temperature scaling applied to logits
        eps = 1e-6
        raw_clipped = min(1.0 - eps, max(eps, raw_conf))
        logit = np.log(raw_clipped / (1.0 - raw_clipped))
        scaled_logit = logit / max(0.01, temperature)
        calib_conf = float(1.0 / (1.0 + np.exp(-scaled_logit)))
        u_calib = float(round(1.0 - calib_conf, 4))

        # 2. Severity S(c)
        severity = compute_severity(pred_label, area_ratio)

        # 3. Faithfulness Guard F_exp(H, T, x)
        faith_res = self.guard.evaluate_faithfulness(prediction, ground_truth_meta)
        faithfulness = faith_res["faithfulness_score"]
        unfaithfulness = float(round(1.0 - faithfulness, 4))

        # Tri-Factor RPI Combination
        rpi_score = (
            self.w1 * u_calib +
            self.w2 * severity +
            self.w3 * unfaithfulness
        )
        rpi_score = float(round(min(1.0, max(0.0, rpi_score)), 4))

        return {
            "rpi_score": rpi_score,
            "u_calib": u_calib,
            "calib_conf": round(calib_conf, 4),
            "severity": severity,
            "faithfulness": faithfulness,
            "unfaithfulness": unfaithfulness,
            "spatial_iou": faith_res["spatial_iou"],
            "text_visual_sim": faith_res["text_visual_sim"]
        }

    def route_batch(
        self,
        records: List[Dict[str, Any]],
        temperature: float = 1.0
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Routes a batch of inspections based on RPI percentile thresholding.
        """
        scored_records = []
        for r in records:
            rpi_info = self.compute_rpi(r["prediction"], r["ground_truth"], temperature)
            merged = {**r, **rpi_info}
            scored_records.append(merged)

        # Determine routing threshold (top routing_target_pct)
        all_scores = [r["rpi_score"] for r in scored_records]
        threshold = float(np.percentile(all_scores, (1.0 - self.routing_target_pct) * 100))

        routed_count = 0
        for r in scored_records:
            is_routed = r["rpi_score"] >= threshold
            r["routed_to_operator"] = is_routed
            if is_routed:
                routed_count += 1

        actual_pct = round((routed_count / max(1, len(scored_records))) * 100.0, 2)
        
        # Compute Auto-Passed subset quality (defect leak rate)
        auto_passed = [r for r in scored_records if not r["routed_to_operator"]]
        fn_leaks = sum(1 for r in auto_passed if r["ground_truth"].get("is_defective", False) and r["prediction"].get("predicted_label") == "normal")

        summary = {
            "total_frames": len(scored_records),
            "routed_count": routed_count,
            "percent_routed": actual_pct,
            "rpi_threshold": round(threshold, 4),
            "auto_passed_count": len(auto_passed),
            "auto_passed_fn_leaks": fn_leaks
        }

        return scored_records, summary


if __name__ == "__main__":
    engine = RPIEngine()
    print("RPIEngine initialized successfully.")
