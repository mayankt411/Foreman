"""
recalibration_engine.py - Active Recalibration & LoRA Refresh Engine

Implements:
1. Temperature scaling via NLL minimization.
2. Expected Calibration Error (ECE) computation (10 bins).
3. Online active recalibration updates from operator feedback.
4. Periodic LoRA adapter memory refresh scaffolding.
"""

import os, sys
import numpy as np
from scipy.optimize import minimize
from typing import Dict, Any, List, Tuple, Optional


class ActiveRecalibrationEngine:
    """
    Manages confidence calibration and adaptive learning from operator feedback.
    """

    def __init__(self, initial_temperature: float = 1.0):
        self.temperature = min(10.0, max(0.1, initial_temperature))
        self.calibration_history = [self.temperature]
        self.operator_feedback_buffer = []
        self.lora_refresh_cache = []

    @staticmethod
    def compute_ece(
        confidences: np.ndarray,
        correctnesses: np.ndarray,
        n_bins: int = 10
    ) -> float:
        """
        Computes Expected Calibration Error (ECE) across n_bins.
        """
        if len(confidences) == 0:
            return 0.0

        bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        n_total = len(confidences)

        for i in range(n_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]
            mask = (confidences >= bin_lower) & (confidences < bin_upper if i < n_bins - 1 else confidences <= bin_upper)
            bin_size = np.sum(mask)

            if bin_size > 0:
                accuracy_in_bin = np.mean(correctnesses[mask])
                avg_conf_in_bin = np.mean(confidences[mask])
                ece += (bin_size / n_total) * abs(accuracy_in_bin - avg_conf_in_bin)

        return float(round(ece * 100.0, 2))  # Return as percentage

    def fit_temperature(
        self,
        raw_confidences: np.ndarray,
        correctnesses: np.ndarray
    ) -> Dict[str, Any]:
        """
        Fits global temperature T via NLL minimization.
        """
        eps = 1e-6
        confs = np.clip(raw_confidences, eps, 1.0 - eps)
        logits = np.log(confs / (1.0 - confs))
        y = correctnesses.astype(np.float64)

        ece_before = self.compute_ece(confs, y)

        def nll_loss(t_val):
            t = max(0.01, float(t_val[0]))
            probs = 1.0 / (1.0 + np.exp(-logits / t))
            probs = np.clip(probs, eps, 1.0 - eps)
            # Binary Cross-Entropy / NLL
            loss = -np.mean(y * np.log(probs) + (1.0 - y) * np.log(1.0 - probs))
            return loss

        res = minimize(nll_loss, x0=[1.0], bounds=[(0.1, 10.0)], method="L-BFGS-B")
        optimal_t = float(round(res.x[0], 3))
        self.temperature = optimal_t
        self.calibration_history.append(optimal_t)

        calib_probs = 1.0 / (1.0 + np.exp(-logits / optimal_t))
        ece_after = self.compute_ece(calib_probs, y)

        return {
            "temperature": optimal_t,
            "ece_before": ece_before,
            "ece_after": ece_after,
            "ece_reduction_pct": round((ece_before - ece_after) / max(0.01, ece_before) * 100.0, 2)
        }

    def ingest_operator_feedback(
        self,
        prediction_id: str,
        operator_action: str,  # "accept" or "reject" / "correct"
        model_confidence: float,
        corrected_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingests a single human-in-the-loop decision and performs online T updating.
        """
        is_correct = (operator_action.lower() == "accept")
        self.operator_feedback_buffer.append({
            "id": prediction_id,
            "action": operator_action,
            "confidence": model_confidence,
            "is_correct": is_correct,
            "corrected_label": corrected_label
        })

        # If overruled, add to LoRA refresh cache
        if not is_correct:
            self.lora_refresh_cache.append(prediction_id)

        # Online temperature step (gradient nudge)
        lr = 0.05
        if not is_correct and model_confidence > 0.70:
            # Model was overconfident on an error -> increase temperature
            self.temperature += lr * (model_confidence - 0.5)
        elif is_correct and model_confidence < 0.60:
            # Model was underconfident on a correct call -> decrease temperature
            self.temperature = max(0.1, self.temperature - lr * (0.5 - model_confidence))

        self.temperature = float(round(min(10.0, max(0.1, self.temperature)), 3))
        self.calibration_history.append(self.temperature)

        return {
            "updated_temperature": self.temperature,
            "total_feedback_count": len(self.operator_feedback_buffer),
            "lora_queue_size": len(self.lora_refresh_cache)
        }


if __name__ == "__main__":
    engine = ActiveRecalibrationEngine()
    sample_confs = np.array([0.95, 0.92, 0.88, 0.65, 0.75, 0.91])
    sample_y = np.array([1, 1, 1, 0, 1, 0])
    fit_res = engine.fit_temperature(sample_confs, sample_y)
    print("Temperature Scaling Fit Result:", fit_res)
