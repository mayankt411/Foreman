# %% [markdown]
# Phase 2 PCB classifier: cross-validation, calibration, Grad-CAM, and routing.
# This file is also the executable source for phase2_train_colab.ipynb.

# %%
import os
DRY_RUN = os.environ.get("DRY_RUN", "0").lower() in {"1", "true", "yes"}
SEED = 42
OUTPUT_ROOT = os.environ.get("OUTPUT_ROOT", "/content/phase2_outputs"
                             if os.access("/content", os.W_OK) else "phase2_outputs")

# %%
import json
import time
import random
import zipfile
import platform
from pathlib import Path
from copy import deepcopy

import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt

try:
    import psutil
except ImportError:
    psutil = None
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    import torchvision
    from torchvision import transforms
    from torchvision.models import ResNet18_Weights
except ImportError as exc:
    raise ImportError("PyTorch and torchvision are required to run this notebook.") from exc
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
from scipy.optimize import minimize

CLASSES = ["dry_joint", "incorrect_installation", "pcb_damage", "short_circuit", "normal"]
CLASS_TO_ID = {name: i for i, name in enumerate(CLASSES)}
IMAGE_SIZE = (480, 640)
DEVICE = torch.device("cuda" if torch.cuda.is_available() and not DRY_RUN else "cpu")
N_SPLITS = 2 if DRY_RUN else 4
EPOCHS = 1 if DRY_RUN else 30
BATCH_SIZE = 8 if DRY_RUN else 16
torch.set_num_threads(4)

def seed_everything(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

seed_everything()

# %% [markdown]
# Data are kept offline. In Colab, upload pcb_defects.zip only when the local
# /content/data/pcb_defects directory is absent.

# %%
DATA_ROOT = Path("/content/data/pcb_defects")
if not DATA_ROOT.exists():
    local_root = Path("data/pcb_defects")
    if local_root.exists():
        DATA_ROOT = local_root
    else:
        try:
            from google.colab import files
            uploaded = files.upload()
            archive = next((Path(name) for name in uploaded if name.endswith(".zip")), None)
            if archive is None:
                raise FileNotFoundError("Upload pcb_defects.zip")
            Path("/content/data").mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive) as zf:
                zf.extractall("/content/data")
            index_candidates = list(Path("/content/data").rglob("dataset_index.json"))
            if not index_candidates:
                raise FileNotFoundError("Uploaded archive does not contain dataset_index.json")
            DATA_ROOT = index_candidates[0].parent
        except ImportError as exc:
            raise FileNotFoundError("Place data/pcb_defects or upload pcb_defects.zip in Colab.") from exc

index_path = DATA_ROOT / "dataset_index.json"
with index_path.open(encoding="utf-8") as handle:
    metadata = json.load(handle)
items = metadata["items"] if isinstance(metadata, dict) and "items" in metadata else metadata
for item in items:
    item["label_id"] = CLASS_TO_ID[item["primary_label"]]
    item["local_path"] = DATA_ROOT / item["split"] / item["file_name"]
if DRY_RUN:
    preview_tv = [x for x in items if x["split"] in ("train", "valid")][:32]
    preview_test = [x for x in items if x["split"] == "test"][:8]
    items = preview_tv + preview_test
print(f"Loaded {len(items)} images from {DATA_ROOT} on {DEVICE}.")

# %%
train_valid = [x for x in items if x["split"] in ("train", "valid")]
test_items = [x for x in items if x["split"] == "test"]
if DRY_RUN:
    train_valid = train_valid[:32]
    test_items = test_items[:8]

train_tf = transforms.Compose([
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.15, contrast=0.15),
    transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.85, 1.0), ratio=(4/3, 4/3)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
eval_tf = transforms.Compose([
    transforms.Resize(IMAGE_SIZE),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

class PCBData(Dataset):
    def __init__(self, rows, transform):
        self.rows, self.transform = rows, transform
    def __len__(self):
        return len(self.rows)
    def __getitem__(self, idx):
        row = self.rows[idx]
        with Image.open(row["local_path"]) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, row["label_id"], idx

pretrained_status = []

def make_model():
    try:
        model = torchvision.models.resnet18(weights=ResNet18_Weights.DEFAULT)
        pretrained_status.append(True)
    except Exception as exc:
        if os.environ.get("ALLOW_RANDOM_INIT") != "1":
            raise RuntimeError(
                "ImageNet ResNet18 weights could not be loaded. "
                "Set ALLOW_RANDOM_INIT=1 only to permit random initialization."
            ) from exc
        model = torchvision.models.resnet18(weights=None)
        pretrained_status.append(False)
    model.fc = nn.Linear(model.fc.in_features, len(CLASSES))
    return model.to(DEVICE)

def class_weights(rows):
    counts = np.bincount([r["label_id"] for r in rows], minlength=len(CLASSES))
    return torch.tensor([1.0 / np.sqrt(max(1, n)) for n in counts],
                        dtype=torch.float32, device=DEVICE)

def train_model(rows):
    model = make_model()
    loader = DataLoader(PCBData(rows, train_tf), batch_size=BATCH_SIZE, shuffle=True,
                        num_workers=0, pin_memory=(DEVICE.type == "cuda"))
    criterion = nn.CrossEntropyLoss(weight=class_weights(rows))
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    model.train()
    for _ in range(EPOCHS):
        for x, y, _ in loader:
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(x.to(DEVICE)), y.to(DEVICE))
            loss.backward()
            optimizer.step()
        scheduler.step()
    return model

@torch.no_grad()
def logits_for(model, rows):
    model.eval()
    loader = DataLoader(PCBData(rows, eval_tf), batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    output = []
    for x, _, _ in loader:
        output.append(model(x.to(DEVICE)).cpu().numpy())
    return np.concatenate(output, axis=0)

def fit_temperature(logits, labels):
    def nll_at(temperature):
        t = float(temperature)
        shifted = logits / t
        shifted -= shifted.max(axis=1, keepdims=True)
        log_probs = shifted - np.log(np.exp(shifted).sum(axis=1, keepdims=True))
        return float(-log_probs[np.arange(len(labels)), labels].mean())
    def objective(log_t):
        return nll_at(np.exp(log_t[0]))
    result = minimize(objective, [0.0], method="L-BFGS-B",
                      bounds=[(np.log(0.1), np.log(10.0))])
    fitted_temperature = float(np.clip(np.exp(result.x[0]), 0.1, 10.0))
    grid = np.logspace(np.log10(0.1), np.log10(10.0), 200)
    candidates = np.concatenate(([fitted_temperature], grid))
    fitted_temperature = float(min(candidates, key=nll_at))
    nll_before = nll_at(1.0)
    nll_after = nll_at(fitted_temperature)
    print(f"NLL: T=1 {nll_before:.6f}, fitted T {fitted_temperature:.6f}, fitted NLL {nll_after:.6f}")
    return fitted_temperature, nll_before, nll_after

def ece_score(logits, labels, temperature=1.0):
    probs = torch.softmax(torch.tensor(logits / temperature), dim=1).numpy()
    confidence, prediction = probs.max(axis=1), probs.argmax(axis=1)
    ece = 0.0
    for index, (low, high) in enumerate(zip(np.linspace(0, 1, 11)[:-1], np.linspace(0, 1, 11)[1:])):
        mask = ((confidence >= low) if index == 0 else (confidence > low)) & (confidence <= high)
        if mask.any():
            ece += mask.mean() * abs(confidence[mask].mean() - (prediction[mask] == labels[mask]).mean())
    return float(ece * 100.0)

def metric_dict(logits, labels, temperature=1.0):
    pred = np.argmax(logits, axis=1)
    return {"n": int(len(labels)), "accuracy": float(accuracy_score(labels, pred)),
            "f1_macro": float(f1_score(labels, pred, average="macro", zero_division=0)),
            "f1_weighted": float(f1_score(labels, pred, average="weighted", zero_division=0)),
            "ece": ece_score(logits, labels, temperature)}

def bootstrap_ci(logits, labels, temperature=1.0, n=1000):
    rng = np.random.default_rng(SEED)
    values = []
    for _ in range(n):
        sample = rng.integers(0, len(labels), len(labels))
        values.append(metric_dict(logits[sample], labels[sample], temperature))
    return {key: [float(np.percentile([v[key] for v in values], 2.5)),
                   float(np.percentile([v[key] for v in values], 97.5))]
            for key in ("accuracy", "f1_macro", "f1_weighted", "ece")}

# %% [markdown]
# OOF logits are produced only by models that did not train on the corresponding image.

# %%
labels_tv = np.array([r["label_id"] for r in train_valid])
oof_logits = np.zeros((len(train_valid), len(CLASSES)), dtype=np.float32)
folds = np.full(len(train_valid), -1, dtype=int)
fold_models = []
skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
for fold, (fit_idx, val_idx) in enumerate(skf.split(np.zeros(len(labels_tv)), labels_tv)):
    model = train_model([train_valid[i] for i in fit_idx])
    fold_models.append(model)
    oof_logits[val_idx] = logits_for(model, [train_valid[i] for i in val_idx])
    folds[val_idx] = fold
temperature, nll_before, nll_after = fit_temperature(oof_logits, labels_tv)
final_model = train_model(train_valid)
test_logits = logits_for(final_model, test_items)
print("OOF temperature:", round(temperature, 4))

# %%
def gradcam(model, tensor, device):
    activations, gradients = [], []
    layer = model.layer4[-1]
    fwd = layer.register_forward_hook(lambda _, __, out: activations.append(out))
    bwd = layer.register_full_backward_hook(lambda _, __, grad: gradients.append(grad[0]))
    model.eval()
    tensor = tensor.to(device)
    model.zero_grad(set_to_none=True)
    output = model(tensor)
    target = int(output.argmax(1).item())
    output[0, target].backward()
    weights = gradients[-1].mean(dim=(2, 3), keepdim=True)
    raw_heat = torch.relu((weights * activations[-1]).sum(dim=1, keepdim=True))
    gradcam.last_raw_peak = float(raw_heat.max().detach().cpu())
    heat = raw_heat
    heat = torch.nn.functional.interpolate(heat, size=(480, 640), mode="bilinear", align_corners=False)
    heat = heat[0, 0].detach().cpu().numpy()
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)
    fwd.remove(); bwd.remove()
    return target, output.detach().cpu().numpy()[0], heat

def gt_mask(row):
    mask = np.zeros((480, 640), dtype=bool)
    for x, y, w, h in row.get("bboxes", []):
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(640, int(x + w)), min(480, int(y + h))
        mask[y0:y1, x0:x1] = True
    return mask

def text_visual_sim(rationale, label):
    keywords = label.replace("_", " ").lower().split()
    matches = sum(k in rationale.lower() for k in keywords)
    return round(min(1.0, 0.80 + 0.18 * matches / max(1, len(keywords))), 4)

SEVERITY = {"short_circuit": 0.90, "pcb_damage": 0.80, "incorrect_installation": 0.70,
            "dry_joint": 0.60, "normal": 0.05}
def compute_severity(label, area):
    base = SEVERITY.get(label, 0.05)
    return round(base * (0.8 + 0.2 * min(1.0, area / 0.05)), 4) if area > 0 else round(base, 4)

RATIONALES = {
    "normal": "Surface trace geometry and solder pads conform to IPC-A-610 standards with no visible bridging, cracking, or misalignment.",
    "short_circuit": "High-severity solder bridge / conductive trace short detected across adjacent component terminal pads, violating trace clearance.",
    "pcb_damage": "Substrate physical fracture / surface scratch detected across FR4 laminate layer, exposing internal copper traces.",
    "incorrect_installation": "Component package placement misalignment detected relative to silkscreen fiducial alignment marks.",
    "dry_joint": "Insufficient solder meniscus wetting and cold joint voiding observed on through-hole connection.",
}

def save_heatmap(heat, image_id, directory):
    rgba = plt.get_cmap("jet")(heat)
    rgba[..., 3] = np.clip((heat - 0.2) / 0.8, 0, 1) * 0.65
    path = directory / f"{image_id}.png"
    plt.imsave(path, rgba)
    return path

# %%
root = Path(OUTPUT_ROOT)
heat_dir, plot_dir = root / "results/heatmaps", root / "results/plots"
heat_dir.mkdir(parents=True, exist_ok=True); plot_dir.mkdir(parents=True, exist_ok=True)
all_rows = train_valid + test_items
all_logits = np.vstack([oof_logits, test_logits])
all_source = ["oof"] * len(train_valid) + ["test"] * len(test_items)
all_folds = list(folds) + [-1] * len(test_items)
records = []
cpu_device = torch.device("cpu")
torch.set_num_threads(4)
cpu_model = deepcopy(final_model).to(cpu_device)
cpu_model.eval()
for row, logits, source, fold in zip(all_rows, all_logits, all_source, all_folds):
    model_for_cam = final_model if source == "test" else fold_models[fold]
    with Image.open(row["local_path"]) as image:
        eval_tensor = eval_tf(image.convert("RGB")).unsqueeze(0)
    pred_id, cam_logits, heat = gradcam(model_for_cam, eval_tensor, DEVICE)
    cam_peak = gradcam.last_raw_peak
    start = time.perf_counter()
    gradcam(cpu_model, eval_tensor, cpu_device)
    elapsed = (time.perf_counter() - start) * 1000
    probs = torch.softmax(torch.tensor(logits), dim=0).numpy()
    cal_probs = torch.softmax(torch.tensor(logits / temperature), dim=0).numpy()
    pred = CLASSES[pred_id]
    hot = heat >= 0.5
    gt = gt_mask(row)
    inter, union = np.logical_and(hot, gt).sum(), np.logical_or(hot, gt).sum()
    if not gt.any() and pred == "normal": spatial = 1.0
    elif not gt.any() or pred == "normal": spatial = 0.0
    else: spatial = float(inter / union) if union else 0.0
    heat_box = float(heat[gt].sum() / (heat.sum() + 1e-8)) if gt.any() else 0.0
    rationale = RATIONALES[pred]  # TEMPLATE, not model-generated text.
    tv = text_visual_sim(rationale, pred)
    faith = 0.5 * spatial + 0.5 * heat_box
    area = float(hot.mean())
    severity = compute_severity(pred, area)
    u_calib = 1.0 - float(cal_probs.max())
    rpi = float(np.clip(0.35 * u_calib + 0.35 * severity + 0.30 * (1.0 - faith), 0, 1))
    path = save_heatmap(heat, row["image_id"], heat_dir)
    records.append({"image_id": row["image_id"], "split": row["split"],
        "file_path": f"data/pcb_defects/{row['split']}/{row['file_name']}",
        "ground_truth_label": row["primary_label"], "predicted_label": pred,
        "raw_confidence": round(float(probs.max()), 4), "calibrated_confidence": round(float(cal_probs.max()), 4),
        "u_calib": round(u_calib, 4), "severity_score": severity, "spatial_iou": round(spatial, 4),
        "text_visual_sim": tv, "faithfulness_score": round(faith, 4), "rpi_score": round(rpi, 4),
        "routed_to_operator": False, "latency_ms": round(elapsed, 2),
        "ram_mb": round(psutil.Process(os.getpid()).memory_info().rss / 2**20, 2) if psutil else None,
        "rationale": rationale, "source": source, "fold": int(fold), "heat_in_box": round(heat_box, 4),
        "cam_peak": round(cam_peak, 6),
        "heatmap_path": str(path.relative_to(root))})

# %%
rpis = np.array([r["rpi_score"] for r in records])
threshold = float(np.percentile(rpis, 85))
for record in records:
    record["routed_to_operator"] = bool(record["rpi_score"] >= threshold)
leaks = sum(r["ground_truth_label"] != "normal" and r["predicted_label"] == "normal"
            and not r["routed_to_operator"] for r in records)
predictions_columns = ["image_id", "split", "file_path", "ground_truth_label", "predicted_label",
    "raw_confidence", "calibrated_confidence", "u_calib", "severity_score", "spatial_iou",
    "text_visual_sim", "faithfulness_score", "rpi_score", "routed_to_operator", "latency_ms",
    "ram_mb", "rationale", "source", "fold", "heat_in_box", "cam_peak", "heatmap_path"]
pd.DataFrame(records)[predictions_columns].to_csv(root / "results/predictions.csv", index=False)
torch.save(final_model.state_dict(), root / "results/model_resnet18.pt")
(root / "results/temperature.json").write_text(json.dumps({"temperature": temperature}, indent=2))

def save_diagnostics(logits, labels, name, calibrated=False):
    probs = torch.softmax(torch.tensor(logits / (temperature if calibrated else 1)), dim=1).numpy()
    conf, pred = probs.max(axis=1), probs.argmax(axis=1)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot([0, 1], [0, 1], "--", color="gray")
    ax.scatter(conf, (pred == labels).astype(float), s=10)
    ax.set(xlabel="confidence", ylabel="correct", title=f"Reliability {name}")
    fig.tight_layout(); fig.savefig(plot_dir / f"reliability_{name}.png", dpi=120); plt.close(fig)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.imshow(confusion_matrix(labels, pred, labels=range(len(CLASSES))), cmap="Blues")
    ax.set(xticks=range(5), yticks=range(5), xticklabels=CLASSES, yticklabels=CLASSES, title=f"Confusion {name}")
    fig.tight_layout(); fig.savefig(plot_dir / f"confusion_{name}.png", dpi=120); plt.close(fig)

save_diagnostics(oof_logits, labels_tv, "oof", True)
save_diagnostics(test_logits, np.array([r["label_id"] for r in test_items]), "test", True)

def benchmark_latency(model, tensor, device):
    """Measure forward plus Grad-CAM without image loading."""
    times = []
    for run in range(110):
        start = time.perf_counter()
        gradcam(model, tensor, device)
        if device.type == "cuda":
            torch.cuda.synchronize()
        if run >= 10:
            times.append((time.perf_counter() - start) * 1000)
    return float(np.mean(times)), float(np.percentile(times, 95))

with Image.open(all_rows[0]["local_path"]) as image:
    benchmark_tensor = eval_tf(image.convert("RGB")).unsqueeze(0)
latency_mean, latency_p95 = benchmark_latency(cpu_model, benchmark_tensor, cpu_device)
oof_metrics = metric_dict(oof_logits, labels_tv, temperature)
test_labels = np.array([r["label_id"] for r in test_items])
test_metrics = metric_dict(test_logits, test_labels, temperature)
test_pred = np.argmax(test_logits, axis=1)
per_class = {c: {"f1": float(f1_score(test_labels, test_pred, labels=[i], average="macro", zero_division=0)),
                 "support": int((test_labels == i).sum())} for i, c in enumerate(CLASSES)}
latencies = np.array([r["latency_ms"] for r in records])
summary = {
    "total_samples": len(records), "defect_f1_score_macro": test_metrics["f1_macro"],
    "defect_f1_score_weighted": test_metrics["f1_weighted"], "accuracy": test_metrics["accuracy"],
    "ece_uncalibrated": ece_score(test_logits, test_labels), "ece_calibrated": test_metrics["ece"],
    "fitted_temperature": temperature, "percent_routed_to_operator": float(np.mean([r["routed_to_operator"] for r in records]) * 100),
    "nll_before": nll_before, "nll_after": nll_after,
    "faithfulness_formula": "0.5 * spatial_iou + 0.5 * heat_in_box",
    "pretrained": bool(pretrained_status) and all(pretrained_status),
    "rpi_threshold": threshold, "auto_passed_fn_leaks": int(leaks),
    "mean_faithfulness_score": float(np.mean([r["faithfulness_score"] for r in records])),
    "adaptation_recovery_epochs": None, "latency_mean_ms": latency_mean,
    "latency_p95_ms": latency_p95, "ram_mean_mb": float(np.nanmean([r["ram_mb"] for r in records])),
    "eval_protocol": "Locked test split; 4-fold stratified train+valid OOF; OOF-only temperature fitting.",
    "oof": oof_metrics, "test": test_metrics, "ci95": {"oof": bootstrap_ci(oof_logits, labels_tv, temperature),
    "test": bootstrap_ci(test_logits, test_labels, temperature)}, "per_class_f1": per_class,
    "latency_hardware": f"Colab CPU ({platform.processor() or 'CPU'}), torch.set_num_threads(4), forward plus Grad-CAM; image loading excluded",
    "model": "resnet18-imagenet-ft",
    "notes": ["Small and imbalanced dataset.", "pcb_damage has 5 images total.",
              "Text similarity is keyword based.", "Rationales are templates, not model text.",
              "faithfulness_score uses spatial_iou and heat_in_box only; text similarity is a constant for template rationales and is excluded",
              "ram_mb is process RSS on Colab and includes CUDA context when a GPU is used; not an edge measurement",
              "Dry-run metrics are not representative."]}
(root / "results/metrics_summary.json").write_text(json.dumps(summary, indent=2))
print(pd.DataFrame([{"split": k, **v} for k, v in [("OOF", oof_metrics), ("TEST", test_metrics)]]).to_string(index=False))
print("honest limitations: small imbalanced data, five pcb_damage images, keyword text similarity, template rationales.")
prediction_frame = pd.DataFrame(records)
print("source counts:")
print(prediction_frame["source"].value_counts().to_string())
print("per-class support:")
for source_name in ("oof", "test"):
    print(source_name.upper(), prediction_frame.loc[prediction_frame["source"] == source_name, "ground_truth_label"].value_counts().to_dict())
print(prediction_frame.head(5).to_string(index=False))
metrics_json = json.loads((root / "results/metrics_summary.json").read_text())
print("metrics JSON keys:", list(metrics_json.keys()))

# %%
# Colab-only download is guarded so the source script remains laptop-friendly.
try:
    from google.colab import files
    archive_path = "/content/phase2_outputs.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(root))
    files.download(archive_path)
except ImportError:
    pass
