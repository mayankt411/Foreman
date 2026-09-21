"""
test_all_components.py - Unit & Integration Tests for XiVLM-Loop
"""

import unittest
import os, sys
import tempfile
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

    def test_recalibration_temperature_clamp(self):
        engine = ActiveRecalibrationEngine(initial_temperature=100.0)
        self.assertEqual(engine.temperature, 10.0)
        engine.temperature = 100.0
        result = engine.ingest_operator_feedback("image-1", "reject", 1.0)
        self.assertEqual(result["updated_temperature"], 10.0)

    def test_windows_path_basename(self):
        from backend.api import windows_basename
        self.assertEqual(windows_basename(r"C:\Users\example\image.jpg"), "image.jpg")

    def test_feedback_endpoint_and_undo(self):
        from fastapi.testclient import TestClient

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "feedback.db")
            os.environ["XIVLM_DB"] = db_path
            import backend.api as api

            api.DB_PATH = db_path
            api._restore_engine([])
            client = TestClient(api.app)

            response = client.post(
                "/api/feedback",
                json={"frame_index": 0, "action": "accept", "override_label": ""},
            )
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["total_logs"], 1)
            self.assertIn("lora_queue_size", body)
            self.assertEqual(len(client.get("/api/feedback/history").json()), 1)

            invalid_action = client.post(
                "/api/feedback",
                json={"frame_index": 0, "action": "invalid", "override_label": ""},
            )
            self.assertEqual(invalid_action.status_code, 400)
            invalid_frame = client.post(
                "/api/feedback",
                json={"frame_index": -1, "action": "accept", "override_label": ""},
            )
            self.assertEqual(invalid_frame.status_code, 404)

            bad_label = client.post(
                "/api/feedback",
                json={"frame_index": 0, "action": "overrule", "override_label": "banana"},
            )
            self.assertEqual(bad_label.status_code, 400)
            missing_label = client.post(
                "/api/feedback",
                json={"frame_index": 0, "action": "overrule", "override_label": ""},
            )
            self.assertEqual(missing_label.status_code, 400)
            good_overrule = client.post(
                "/api/feedback",
                json={"frame_index": 0, "action": "overrule", "override_label": "normal"},
            )
            self.assertEqual(good_overrule.status_code, 200)
            self.assertEqual(client.get("/api/feedback/history").json()[-1]["override_label"], "normal")
            self.assertTrue(client.post("/api/feedback/undo").json()["success"])
            health = client.get("/api/health").json()
            self.assertNotEqual(health["version"], "2.1.0")

            undo = client.post("/api/feedback/undo")
            self.assertEqual(undo.status_code, 200)
            self.assertTrue(undo.json()["success"])
            self.assertEqual(undo.json()["total_logs"], 0)

    def test_heatmap_and_recompute_endpoints(self):
        from fastapi.testclient import TestClient
        import backend.api as api

        client = TestClient(api.app)
        preds = client.get("/api/predictions").json()
        self.assertEqual(len(preds), 189)
        self.assertTrue(all(p["has_heatmap"] for p in preds))
        heat = client.get(preds[0]["heatmap_url"])
        self.assertEqual(heat.status_code, 200)
        self.assertEqual(heat.headers["content-type"], "image/png")
        self.assertEqual(client.get("/api/heatmap/9999").status_code, 404)
        self.assertEqual(client.get("/api/plots/reliability_oof").status_code, 200)
        self.assertEqual(client.get("/api/plots/../../etc/passwd").status_code, 404)
        self.assertEqual(client.get("/api/plots/banana").status_code, 404)
        self.assertEqual(client.get("/api/image/0").status_code, 200)

        at_fit = client.get(f"/api/recompute?temperature={api.FITTED_TEMPERATURE}").json()
        self.assertEqual(len(at_fit["frames"]), 189)
        for frame, pred in zip(at_fit["frames"], preds):
            self.assertAlmostEqual(frame["rpi_score"], pred["rpi_score"], places=2)
        hot = client.get("/api/recompute?temperature=5").json()
        cold = client.get("/api/recompute?temperature=0.5").json()
        self.assertGreater(hot["frames"][3]["u_calib"], cold["frames"][3]["u_calib"])
        self.assertEqual(client.get("/api/recompute?temperature=99").json()["temperature"], 10.0)


if __name__ == "__main__":
    unittest.main()
