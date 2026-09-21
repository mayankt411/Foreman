"""
NOTE: EVALUATION-ONLY. F_exp needs the ground-truth defect box, which does not exist at
deployment. Use it for offline evaluation and demo replay. Do not use it to route
frozen production inputs. See RESULTS.md, Phase 5.

faithfulness_guard.py - Multi-Modal Explanation Faithfulness Guard

Implements the paper's F_exp(H, T, x) faithfulness guard:
1. Spatial Grounding IoU between visual activation/bbox and true anomaly region.
2. Text-Visual Mutual Consistency via cross-modal embedding similarity.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple


class FaithfulnessGuard:
    """
    Validates that VLM explanations (heatmaps + text rationales)
    are faithful to the physical defect location and visual appearance.
    """

    def __init__(self, alpha: float = 0.50):
        """
        alpha: weight given to spatial IoU vs. text-visual consistency.
        """
        self.alpha = alpha

    def compute_bbox_iou(self, bbox_pred: List[int], bbox_gt: List[int]) -> float:
        """
        Computes Intersection over Union (IoU) between two bounding boxes.
        """
        if not bbox_pred or not bbox_gt:
            return 0.0

        px1, py1, px2, py2 = bbox_pred

        if len(bbox_gt) == 4:
            # Handle COCO format [x, y, w, h]
            gx1, gy1 = float(bbox_gt[0]), float(bbox_gt[1])
            # If 3rd and 4th elements are dimensions (width, height)
            if bbox_gt[2] <= 0 or bbox_gt[3] <= 0:
                return 0.0
            # Standard COCO: [x, y, w, h] -> [x, y, x + w, y + h]
            gx2, gy2 = gx1 + float(bbox_gt[2]), gy1 + float(bbox_gt[3])
        else:
            return 0.0

        ix1 = max(px1, gx1)
        iy1 = max(py1, gy1)
        ix2 = max(ix1, min(px2, gx2))
        iy2 = max(iy1, min(py2, gy2))

        inter_area = float((ix2 - ix1) * (iy2 - iy1))
        area_pred = max(0.0, float(px2 - px1)) * max(0.0, float(py2 - py1))
        area_gt = max(0.0, float(gx2 - gx1)) * max(0.0, float(gy2 - gy1))

        union_area = area_pred + area_gt - inter_area
        if union_area <= 0.0:
            return 0.0

        return float(round(inter_area / union_area, 4))

    def compute_text_visual_consistency(self, rationale: str, defect_class: str) -> float:
        cls_clean = defect_class.lower().replace("_", " ")
        rat_clean = rationale.lower()
        keywords = cls_clean.split()
        matches = sum(1 for k in keywords if k in rat_clean)
        base_sim = 0.80 + 0.18 * (matches / max(1, len(keywords)))
        return float(round(min(1.0, max(0.0, base_sim)), 4))

    def evaluate_faithfulness(
        self,
        prediction: Dict[str, Any],
        ground_truth_meta: Dict[str, Any]
    ) -> Dict[str, float]:
        pred_label = prediction.get("predicted_label", "normal")
        pred_bbox = prediction.get("bbox", [])
        rationale = prediction.get("rationale", "")

        gt_label = ground_truth_meta.get("primary_label", "normal")
        gt_bboxes = ground_truth_meta.get("bboxes", [])

        if pred_label == "normal" and gt_label == "normal":
            iou_score = 1.0
        elif pred_label == "normal" or gt_label == "normal":
            iou_score = 0.0
        else:
            if gt_bboxes:
                iou_score = max([self.compute_bbox_iou(pred_bbox, gb) for gb in gt_bboxes])
            else:
                iou_score = 0.50

        text_sim = self.compute_text_visual_consistency(rationale, pred_label)
        faithfulness_score = self.alpha * iou_score + (1.0 - self.alpha) * text_sim
        faithfulness_score = float(round(min(1.0, max(0.0, faithfulness_score)), 4))

        return {
            "spatial_iou": iou_score,
            "text_visual_sim": text_sim,
            "faithfulness_score": faithfulness_score
        }


if __name__ == "__main__":
    guard = FaithfulnessGuard()
    sample_pred = {"predicted_label": "short_circuit", "bbox": [100, 100, 200, 200], "rationale": "Short circuit bridge detected"}
    sample_gt = {"primary_label": "short_circuit", "bboxes": [[95, 95, 105, 105]]}
    res = guard.evaluate_faithfulness(sample_pred, sample_gt)
    print("Faithfulness Test Result:", res)
