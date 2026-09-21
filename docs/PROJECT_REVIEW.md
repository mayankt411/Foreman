# Project Review: XiVLM-Loop

Date: 2026-09-21. Scope: what the project is, what was fixed, what remains.

## What was wrong at the start
1. Inference was simulated. Reported F1, ECE and latency described the simulator.
2. Feedback did not persist and the dashboard temperature was fake.
3. Windows paths in the data files broke image and box lookups on macOS.
4. The UI showed hard-coded simulator numbers, fake per-class F1 and fake baselines.

## What was done
| Phase | Result |
| :--- | :--- |
| 1 | SQLite feedback with undo, label validation, path fix, honesty notes |
| 2 | ResNet18 fine-tune with Grad-CAM. 4-fold OOF plus locked test. OOF-only temperature fit |
| 3 | Backend serves real predictions, heatmaps, plots, live recompute |
| 4 | Heatmap overlay, banner, sorted queue, stacked RPI bar, calibration panel |
| 5 | RPI ablation, learned weights, per-class ECE, honest RESULTS.md |
| 6 | README rewrite, this review, faithfulness labelled offline-only |

## Key findings
1. Test accuracy is 58% (95% CI 42 to 75%). The model is weak on 36 images.
2. Faithfulness uses the ground-truth box. It cannot run in production.
3. Severity carries no error signal. It is a priority weight, not a detector.
4. The full RPI caught 0 of 6 missed defects at a 15% budget.
5. Latency is about 17 times over target. No edge hardware was tested.

## Open work
1. Replace `F_exp` in routing with a model-only signal (Grad-CAM concentration gave AUROC 0.77 with U).
2. Improve heatmaps: layer3 plus layer4 CAM, or box-supervised fine-tuning.
3. Reduce latency: 288x384 input, forward-only timing, ONNX or quantization, then test on real edge hardware.
4. Rebalance classes (stronger weights or focal loss). Collect more `pcb_damage` images.
5. Save full logits so live calibration is exact.
6. Retake UI screenshots.
7. Remove the old simulator (`src/inference_pipeline.py`, `src/evaluate_benchmark.py`) or move it to `legacy/`.
8. Delete `frontend/src/components/ECERecoveryChart.jsx`. It is unused and holds fake simulator numbers.
9. Keep one canonical clone. Two clones existed during this work.
