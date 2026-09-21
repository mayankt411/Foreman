# XiVLM-Loop: Human-in-the-Loop PCB Defect Inspection with Calibration and Heatmaps

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.0%2B-61DAFB.svg)](https://reactjs.org/)

## Status: research prototype

The classifier is a **ResNet18 fine-tuned from ImageNet weights**, with **Grad-CAM heatmaps**. It is **not a vision-language model**. Rationales are templates, not model text. Results come from 189 images and carry wide error bars. See `RESULTS.md` for every number and limitation.

Older versions of this repo reported 95% F1 and 3 ms latency. Those numbers came from a simulator and are archived in `docs/RESULTS_simulated_baseline.md`. Do not cite them.

---

## Screenshots

![Inspection console, nominal frame](docs/images/dashboard_inspection_console.png)
![Defect frame with Grad-CAM attention overlay](docs/images/defect_inspection_detail.png)
![Measured results and calibration plots](docs/images/benchmark_results_and_ece.png)

## What it does

1. **Classifies** a PCB image into five classes: `dry_joint`, `incorrect_installation`, `pcb_damage`, `short_circuit`, `normal`.
2. **Explains** with a Grad-CAM heatmap (red = high attention, green = low).
3. **Calibrates** confidence with temperature scaling (T = 2.12, fitted on out-of-fold predictions only).
4. **Routes** the highest-priority 15% of frames to a human operator using the Review-Priority Index (RPI).
5. **Learns from feedback**: operator accept or overrule actions update the temperature live and are stored in SQLite.

## Headline results

| Metric | Out-of-fold (n=153) | Locked test (n=36) |
| :--- | :---: | :---: |
| Accuracy | 79.1% | 58.3% |
| F1 macro | 0.662 | 0.454 |
| ECE (calibrated) | 5.0% | 14.6% |

- Test intervals are wide (test F1 macro 95% CI 0.31 to 0.68). `pcb_damage` has 5 images in total.
- 15.3% of frames are routed (RPI threshold 0.677). 6 defects in 189 images were auto-passed as normal.
- Latency is 832 ms mean on a Colab CPU including Grad-CAM. The 50 ms target is **not met**. No edge device was tested.
- Mean heat inside the defect box is only 15%. Heatmaps often miss the defect.

## RPI

```
RPI = 0.35 * U_calib + 0.35 * S(class) + 0.30 * (1 - F_exp)
```

- `U_calib`: calibrated uncertainty, 1 minus calibrated confidence.
- `S(class)`: consequence score. short_circuit 0.90, pcb_damage 0.80, incorrect_installation 0.70, dry_joint 0.60, normal 0.05, scaled by defect area.
- `F_exp`: faithfulness, `0.5 * spatial IoU + 0.5 * heat-in-box`.

**Caveat.** `F_exp` is measured against the ground-truth defect box. That box does not exist in production, so `F_exp` is an **offline evaluation metric**, not a deployable signal. The dashboard replays RPI on stored predictions. In the Phase 5 ablation (`RESULTS.md`), severity carries no error signal, and the full RPI caught none of the 6 missed defects at a 15% review budget.

## Live temperature note

Only the max-softmax value was stored, not full logits. The dashboard's live recompute (`/api/recompute`) uses a binary approximation, offset so it matches the shipped multiclass values at the fitted temperature. It shows trends, not exact numbers.

---

## Project layout

```
backend/api.py                  FastAPI service, SQLite feedback, heatmap and plot endpoints
frontend/                       React operator console (Vite, Tailwind)
notebooks/phase2_train_colab.*  Training, Grad-CAM, temperature fit (run on Colab)
tools/phase5_eval.py            RPI ablation, learned weights, per-class ECE
tools/phase5_plots.py           Reliability diagrams and confusion matrices
results/                        predictions.csv, metrics_summary.json, phase5_eval.json,
                                heatmaps/, plots/, model_resnet18.pt, temperature.json
src/                            severity, faithfulness guard, RPI engine, recalibration engine
tests/test_all_components.py    8 tests
docs/                           archived simulator results, project review
data/pcb_defects/               189 images, 459 boxes (128 train, 25 valid, 36 test)
```

Note: `src/inference_pipeline.py` and `src/evaluate_benchmark.py` are the **old simulator**. They are not used by the app or the reported results.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
python run_app.py               # or: python -m uvicorn backend.api:app --port 8000
```

Open http://localhost:8000.

## Operator console

- Image feed with heatmap overlay, opacity slider, box toggle, and two views: **Defect zone** (truth boxes) and **Model attention** (heatmap).
- PASS or REVIEW banner with RPI and threshold.
- Queue sorted by RPI, with an Only routed filter.
- Stacked RPI bar: uncertainty, severity, unfaithfulness.
- Calibration panel: reliability diagrams and confusion matrices, OOF and test, with 95% CIs.
- Feedback: `[A]` accept, `[O]` overrule, `[U]` undo. Stored in `backend/feedback.db`.
- Temperature slider recomputes RPI and routing live.

## Reproduce

```bash
python -m unittest tests.test_all_components     # tests
python tools/phase5_eval.py                      # ablation, learned weights, per-class ECE
```

Retraining: open `notebooks/phase2_train_colab.ipynb` in Colab (T4 GPU), upload `pcb_defects.zip` (the zipped `data/pcb_defects` folder), run all, then copy `results/` from the downloaded zip into this repo.

## Known limitations

- Tiny, imbalanced data. Small test set. `pcb_damage` metrics are not meaningful.
- The model over-predicts `incorrect_installation`.
- LoRA refresh is a scaffold. No adapter is trained.

## License

MIT. See [LICENSE](LICENSE).
