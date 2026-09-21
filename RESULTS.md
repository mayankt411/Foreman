# XiVLM-Loop: Results Report

**Title**: Explainable Human-in-the-Loop Inspection with Active Recalibration for Edge Manufacturing

All numbers below come from a real fine-tuned model (ResNet18, ImageNet weights, Grad-CAM heatmaps) trained in `notebooks/phase2_train_colab.ipynb`. The earlier simulator numbers are archived in `docs/RESULTS_simulated_baseline.md` and must not be cited.

**Evaluation protocol.** 189 images. 153 train+valid images are scored out-of-fold (4-fold stratified CV, seed 42). 36 test images are a locked split, never used for training or temperature fitting. Temperature is fitted on out-of-fold predictions only. Confidence intervals are 95% bootstrap.

---

## 1. Measured Results

| Metric | OOF (n=153) | Locked test (n=36) | Notes |
| :--- | :---: | :---: | :--- |
| Accuracy | 79.1% [72.5, 85.6] | 58.3% [41.7, 75.0] | Test interval is wide |
| F1 macro | 0.662 [0.540, 0.780] | 0.454 [0.314, 0.681] | pcb_damage has 5 images in total |
| F1 weighted | 0.778 [0.705, 0.849] | 0.556 [0.373, 0.724] | |
| ECE, calibrated | 5.0% [4.4, 13.0] | 14.6% [11.0, 30.9] | Reported as percent, 10 bins |
| ECE, uncalibrated | not reported | 28.2% | Test split, T=1 |
| Fitted temperature | 2.12 | | NLL 0.911 to 0.673 on OOF |

| System metric | Value | Notes |
| :--- | :---: | :--- |
| Frames routed to operator | 15.3% (29 of 189) | RPI threshold 0.677 (85th percentile of RPI) |
| Defects auto-passed as normal | 6 | Missed defects across all 189 images |
| Mean faithfulness | 0.194 | 0.5 x spatial IoU + 0.5 x heat-in-box. Heatmaps often miss the defect |
| Latency | 832 ms mean, 1125 ms p95 | Colab CPU, 4 threads, forward plus Grad-CAM. Target of 50 ms is NOT met |
| RAM | 2078 MB | Colab process RSS. Not an edge measurement |
| Adaptation recovery epochs | not measured | Earlier "3 iterations" came from the simulator |

Per-class F1 on the test split: dry_joint 0.40 (n=10), incorrect_installation 0.78 (n=10), short_circuit 0.53 (n=6), normal 0.56 (n=9), pcb_damage 0.00 (n=1, not meaningful).

---

## 2. Phase 5 Evaluation (see `results/phase5_eval.json`, `tools/phase5_eval.py`)

Question: which RPI parts find model errors? Score is judged on frames where prediction differs from truth (25% of images). Review budget is the top 15% of frames.

| Score | AUROC for errors [95% CI] | Errors caught in top 15% | Missed defects caught (of 6) |
| :--- | :---: | :---: | :---: |
| Random | 0.50 | 15% | 15% |
| 1 - raw confidence | 0.742 [0.659, 0.816] | 28% | 33% |
| U (calibrated uncertainty) | 0.751 [0.668, 0.834] | 30% | 50% |
| Severity only | 0.492 [0.393, 0.583] | 17% | 0% |
| Unfaithfulness only | 0.836 [0.759, 0.905] | 49% | 50% |
| U + unfaithfulness | 0.851 [0.795, 0.902] | 38% | 67% |
| Full RPI 0.35/0.35/0.30 | 0.760 [0.678, 0.830] | 34% | 0% |
| Low Grad-CAM peak (no truth box) | 0.736 [0.662, 0.805] | 23% | 33% |
| U + low Grad-CAM peak (no truth box) | 0.769 [0.696, 0.836] | 34% | 50% |

Findings:
1. Calibrated uncertainty beats raw confidence only slightly. Intervals overlap.
2. Severity carries no error signal (AUROC 0.49). That is expected: severity ranks consequence, not correctness. It belongs in the RPI as a business priority, not as an error detector.
3. Unfaithfulness is the strongest signal, but it is computed against the ground-truth defect box. That box does not exist at deployment. Treat this AUROC as an oracle upper bound, not a deployable result. The deployable comparison is the last two rows.
4. The full RPI caught none of the 6 missed defects at a 15% budget. Severity dilutes the uncertainty signal.
5. Learned weights (logistic regression on OOF, judged on test): U 0.42, severity 0.02, unfaithfulness 0.56. Test AUROC 0.91 vs 0.80 for default weights, but n=36 and the fit uses the oracle box. Errors caught at 15% budget were equal (33%). Not enough evidence to change the default weights.

Per-class ECE (percent, by predicted class): incorrect_installation 10.2 (n=111), short_circuit 10.3 (n=34), dry_joint 13.1 (n=19), normal 15.6 (n=23), pcb_damage 45.0 (n=2). Only the first two have 30 or more predictions. The rest are indicative only.

---

## 3. Honest Limitations

- Tiny, imbalanced dataset. Test intervals are wide. pcb_damage has 5 images and its metrics are meaningless.
- Faithfulness uses the ground-truth box, so it cannot run at deployment as defined. A deployable version needs a model-only signal.
- Grad-CAM heatmaps often miss the defect (mean heat inside the box 15%). The system should not be called explainable at this quality without further work.
- Latency is about 17 times over the 50 ms target on Colab CPU. No edge hardware was tested. Options: smaller input (288x384), forward-only timing, ONNX or quantization.
- The model over-predicts incorrect_installation (111 predictions for 88 correct).
- Live temperature updates in the UI use a binary approximation of the multiclass calibration, offset to match at the fitted temperature. They show trends, not exact values. Only max-softmax was stored, not full logits.
- Text similarity is keyword based and rationales are templates, not model text. Text similarity is excluded from faithfulness.
- LoRA refresh is a scaffold. No adapter is trained.

---

## 4. System Artifacts
- `notebooks/phase2_train_colab.ipynb` and `.py`: training, Grad-CAM, temperature fit, RPI
- `tools/phase5_eval.py`: RPI ablation, learned weights, per-class ECE
- `results/predictions.csv`: predictions for 189 images (OOF and test)
- `results/metrics_summary.json`: metrics with CIs and a `phase5` summary
- `results/phase5_eval.json`: full Phase 5 output
- `results/heatmaps/`: Grad-CAM RGBA overlays
- `results/plots/`: reliability diagrams and confusion matrices, OOF and test
- `results/model_resnet18.pt`, `results/temperature.json`
- `src/`: severity, faithfulness guard, RPI engine, recalibration engine
- `backend/api.py`, `frontend/`: FastAPI service and React operator console
- `tests/test_all_components.py`: test suite
