"""
test_all_components.py - Unit & Integration Tests for XiVLM-Loop
"""

import unittest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.severity import compute_severity, CLASS_SEVERITY_TIERS
from src.faithfulness_guard import FaithfulnessGuard
from src.rpi_engine import RPIEngine
from src.recalibration_engine import ActiveRecalibrationEngine


class TestXiVLMComponents(unittest.TestCase):

    def test_severity_bounds_and_ordering(self):
        short_sev = compute_severity("short_circuit")
        damage_sev = compute_severity("pcb_damage")
        joint_sev = compute_severity("dry_joint")
        normal_sev = compute_severity("normal")

        self.assertGreater(short_sev, damage_sev)
        self.assertGreater(damage_sev, joint_sev)
        self.assertGreater(joint_sev, normal_sev)
        self.assertLessEqual(short_sev, 1.0)
        self.assertGreaterEqual(normal_sev, 0.0)

    def test_faithfulness_guard_iou(self):
        guard = FaithfulnessGuard()
        # Exact match iou
        iou_exact = guard.compute_bbox_iou([50, 50, 150, 150], [50, 50, 100, 100])
        self.assertAlmostEqual(iou_exact, 1.0, places=2)

        # Non-overlapping iou
        iou_zero = guard.compute_bbox_iou([0, 0, 10, 10], [100, 100, 50, 50])
        self.assertEqual(iou_zero, 0.0)

    def test_rpi_engine_formulation(self):
        engine = RPIEngine(w1=0.35, w2=0.35, w3=0.30)
        pred = {"predicted_label": "short_circuit", "confidence": 0.75, "bbox": [10, 10, 50, 50], "rationale": "Solder short"}
        gt = {"primary_label": "short_circuit", "area_ratio": 0.02, "bboxes": [[10, 10, 40, 40]]}
        res = engine.compute_rpi(pred, gt, temperature=1.0)
        self.assertIn("rpi_score", res)
        self.assertGreaterEqual(res["rpi_score"], 0.0)
        self.assertLessEqual(res["rpi_score"], 1.0)

    def test_recalibration_ece_and_temperature(self):
        engine = ActiveRecalibrationEngine()
        confs = np.array([0.95, 0.92, 0.88, 0.60, 0.70, 0.90])
        y = np.array([1, 1, 1, 0, 1, 0])
        fit_out = engine.fit_temperature(confs, y)
        self.assertGreater(fit_out["temperature"], 0.0)
        self.assertLessEqual(fit_out["ece_after"], fit_out["ece_before"])


if __name__ == "__main__":
    unittest.main()
