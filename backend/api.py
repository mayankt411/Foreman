import os
import sys
import json
import math
import ntpath
import platform
import sqlite3
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.recalibration_engine import ActiveRecalibrationEngine

APP_VERSION = "2.3.0"
VALID_LABELS = {"dry_joint", "incorrect_installation", "pcb_damage", "short_circuit", "normal"}

app = FastAPI(title="XiVLM-Loop Telemetry & Inspection API", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://localhost:5173", "http://localhost:8000",
        "http://127.0.0.1:3000", "http://127.0.0.1:5173", "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "pcb_defects")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
DB_PATH = os.environ.get("XIVLM_DB", os.path.join(BASE_DIR, "backend", "feedback.db"))
_db_lock = threading.RLock()
_predictions_cache = None
_predictions_mtime = None


def windows_basename(path):
    return ntpath.basename(str(path))


def _load_predictions():
    global _predictions_cache, _predictions_mtime
    csv_path = os.path.join(RESULTS_DIR, "predictions.csv")
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Predictions not found")
    mtime = os.stat(csv_path).st_mtime_ns
    if _predictions_cache is None or _predictions_mtime != mtime:
        _predictions_cache = pd.read_csv(csv_path)
        _predictions_mtime = mtime
    return _predictions_cache


def _db_connection():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            frame_index INTEGER NOT NULL,
            action TEXT NOT NULL,
            override_label TEXT NOT NULL,
            model_confidence REAL NOT NULL,
            temperature REAL NOT NULL
        )"""
    )
    connection.commit()
    return connection


def _feedback_rows():
    with _db_lock:
        with _db_connection() as connection:
            return connection.execute(
                "SELECT id, ts, frame_index, action, override_label, model_confidence, temperature "
                "FROM feedback ORDER BY id"
            ).fetchall()


def _restore_engine(rows):
    engine.temperature = initial_temperature
    engine.calibration_history = [initial_temperature]
    engine.operator_feedback_buffer.clear()
    engine.lora_refresh_cache.clear()
    for row in rows:
        engine.ingest_operator_feedback(
            prediction_id=str(row["frame_index"]),
            operator_action="accept" if row["action"] == "accept" else "reject",
            model_confidence=float(row["model_confidence"]),
            corrected_label=row["override_label"],
        )
        engine.temperature = float(row["temperature"])


with open(os.path.join(RESULTS_DIR, "metrics_summary.json"), "r", encoding="utf-8") as metrics_file:
    _metrics = json.load(metrics_file)
initial_temperature = float(_metrics.get("fitted_temperature", 1.0))
FITTED_TEMPERATURE = initial_temperature
RPI_THRESHOLD = float(_metrics.get("rpi_threshold", 0.35))
MODEL_NAME = _metrics.get("model", "simulated")
RPI_WEIGHTS = (0.35, 0.35, 0.30)
engine = ActiveRecalibrationEngine(initial_temperature=initial_temperature)

# Load dataset index if available to enrich predictions with exact bounding boxes
dataset_index_map = {}
dataset_index_path = os.path.join(DATA_DIR, "dataset_index.json")
if os.path.exists(dataset_index_path):
    try:
        with open(dataset_index_path, "r", encoding="utf-8") as f:
            idx_list = json.load(f)
            for item in idx_list:
                fname = item.get("file_name") or windows_basename(item.get("file_path", ""))
                if fname:
                    dataset_index_map[fname] = item
                img_id = item.get("image_id")
                if img_id:
                    dataset_index_map[img_id] = item
    except Exception as e:
        print(f"[Warning] Failed to load dataset_index.json: {e}")

@app.get("/api/health")
def health():
    return {
        "status": "online",
        "system": "XiVLM-Loop Inference Engine",
        "device": f"{platform.system()} {platform.machine()}",
        "version": APP_VERSION,
        "model": MODEL_NAME,
        "real_model": bool(_metrics.get("pretrained", False)),
    }

@app.get("/api/metrics")
def get_metrics():
    metrics_path = os.path.join(RESULTS_DIR, "metrics_summary.json")
    if not os.path.exists(metrics_path):
        raise HTTPException(status_code=404, detail="Metrics summary not found")
    with open(metrics_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/plots/{name}")
def get_plot(name: str):
    if name not in {"reliability_oof", "reliability_test", "confusion_oof", "confusion_test"}:
        raise HTTPException(status_code=404, detail="Plot not found")
    plot_path = os.path.join(RESULTS_DIR, "plots", f"{name}.png")
    if not os.path.exists(plot_path):
        raise HTTPException(status_code=404, detail="Plot not found")
    return FileResponse(plot_path, media_type="image/png")


@app.get("/api/predictions")
def get_predictions():
    df = _load_predictions()
    records = []
    for idx, row in df.iterrows():
        item = {key: (None if pd.isna(value) else value) for key, value in row.to_dict().items()}
        file_path = str(row.get("file_path", ""))
        fname = windows_basename(file_path)
        img_id = str(row.get("image_id", ""))
        
        # Enrich with bounding boxes from dataset index if available
        meta = dataset_index_map.get(fname) or dataset_index_map.get(img_id) or {}
        item["bboxes"] = meta.get("bboxes", [])
        item["num_defects"] = meta.get("num_defects", len(meta.get("bboxes", [])))
        item["width"] = meta.get("width", 640)
        item["height"] = meta.get("height", 480)
        item["index"] = idx
        item["file_name"] = fname
        item["image_url"] = f"/api/image/{idx}"
        has_heat = _heatmap_path(row) is not None
        item["has_heatmap"] = has_heat
        item["heatmap_url"] = f"/api/heatmap/{idx}" if has_heat else None
        records.append(item)
    return records

@app.get("/api/image/{idx}")
def get_image(idx: int):
    df = _load_predictions()
    if idx < 0 or idx >= len(df):
        raise HTTPException(status_code=404, detail="Frame index out of bounds")
    
    file_path = str(df.iloc[idx]["file_path"])
    if not os.path.isabs(file_path):
        file_path = os.path.join(BASE_DIR, file_path)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/jpeg")
    
    fname = windows_basename(file_path)
    split = str(df.iloc[idx].get("split", ""))
    search_splits = [split] + [candidate for candidate in ["test", "train", "valid"] if candidate != split]
    for sub in search_splits:
        alt_path = os.path.join(DATA_DIR, sub, fname)
        if os.path.exists(alt_path):
            return FileResponse(alt_path, media_type="image/jpeg")
            
    raise HTTPException(status_code=404, detail=f"Image file not found: {fname}")

def _heatmap_path(row):
    """Return absolute path of the Grad-CAM RGBA PNG for a prediction row, or None."""
    candidates = []
    raw = row.get("heatmap_path")
    if isinstance(raw, str) and raw.strip():
        name = windows_basename(raw.replace("/", "\\"))
        candidates.append(os.path.join(RESULTS_DIR, "heatmaps", name))
    candidates.append(os.path.join(RESULTS_DIR, "heatmaps", f"{row.get('image_id')}.png"))
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


@app.get("/api/heatmap/{idx}")
def get_heatmap(idx: int):
    df = _load_predictions()
    if idx < 0 or idx >= len(df):
        raise HTTPException(status_code=404, detail="Frame index out of bounds")
    path = _heatmap_path(df.iloc[idx].to_dict())
    if path is None:
        raise HTTPException(status_code=404, detail="No heatmap for this frame")
    return FileResponse(path, media_type="image/png")


def _live_confidence(raw_conf, shipped_cal, temperature):
    """Recompute calibrated confidence at a live temperature.

    Only max-softmax is stored, so live updates use a binary logit(p)/T rule.
    An offset makes the result equal the shipped multiclass value at the fitted T.
    """
    eps = 1e-6
    p = min(max(float(raw_conf), eps), 1 - eps)
    logit = math.log(p / (1 - p))
    def binary(t):
        return 1.0 / (1.0 + math.exp(-logit / t))
    live = binary(temperature) + (float(shipped_cal) - binary(FITTED_TEMPERATURE))
    return min(1.0, max(0.0, live))


@app.get("/api/recompute")
def recompute(temperature: float = None):
    """Recompute u_calib, RPI and routing per frame for a live temperature."""
    t = engine.temperature if temperature is None else min(10.0, max(0.1, float(temperature)))
    df = _load_predictions()
    w_u, w_s, w_f = RPI_WEIGHTS
    frames = []
    for idx, row in df.iterrows():
        conf = _live_confidence(row["raw_confidence"], row["calibrated_confidence"], t)
        u = 1.0 - conf
        rpi = w_u * u + w_s * float(row["severity_score"]) + w_f * (1.0 - float(row["faithfulness_score"]))
        frames.append({
            "index": int(idx),
            "calibrated_confidence": round(conf, 4),
            "u_calib": round(u, 4),
            "rpi_score": round(rpi, 4),
            "routed_to_operator": bool(rpi >= RPI_THRESHOLD),
        })
    return {
        "temperature": t,
        "fitted_temperature": FITTED_TEMPERATURE,
        "rpi_threshold": RPI_THRESHOLD,
        "routed_count": sum(f["routed_to_operator"] for f in frames),
        "frames": frames,
    }


class FeedbackPayload(BaseModel):
    frame_index: int
    action: str
    override_label: str = ""

@app.post("/api/feedback")
def post_feedback(payload: FeedbackPayload):
    if payload.action not in {"accept", "overrule"}:
        raise HTTPException(status_code=400, detail="Action must be accept or overrule")
    if payload.action == "overrule" and payload.override_label not in VALID_LABELS:
        raise HTTPException(
            status_code=400,
            detail=f"override_label must be one of {sorted(VALID_LABELS)}",
        )
    override_label = payload.override_label if payload.action == "overrule" else ""
    df = _load_predictions()
    if payload.frame_index < 0 or payload.frame_index >= len(df):
        raise HTTPException(status_code=404, detail="Frame index out of bounds")
    row = df.iloc[payload.frame_index]
    raw_conf = float(row["raw_confidence"])
    timestamp = pd.Timestamp.now().strftime("%H:%M:%S")
    with _db_lock:
        result = engine.ingest_operator_feedback(
            prediction_id=str(row["image_id"]),
            operator_action="accept" if payload.action == "accept" else "reject",
            model_confidence=raw_conf,
            corrected_label=override_label or None,
        )
        try:
            with _db_connection() as connection:
                connection.execute(
                    "INSERT INTO feedback (ts, frame_index, action, override_label, model_confidence, temperature) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (timestamp, payload.frame_index, payload.action, override_label,
                     raw_conf, result["updated_temperature"]),
                )
        except Exception as exc:
            # Keep engine and database in sync: rebuild engine from what is stored.
            _restore_engine(_feedback_rows())
            raise HTTPException(status_code=500, detail=f"feedback not saved: {exc}")
    log_entry = {
        "frame_index": payload.frame_index,
        "action": payload.action,
        "override_label": override_label,
        "model_confidence": raw_conf,
        "temperature": result["updated_temperature"],
        "timestamp": timestamp,
    }
    return {
        "success": True,
        "new_temperature": result["updated_temperature"],
        "log": log_entry,
        "total_logs": result["total_feedback_count"],
        "lora_queue_size": result["lora_queue_size"],
    }

@app.get("/api/feedback/history")
def get_feedback_history():
    return [
        {
            "frame_index": row["frame_index"],
            "action": row["action"],
            "override_label": row["override_label"],
            "model_confidence": row["model_confidence"],
            "temperature": row["temperature"],
            "timestamp": row["ts"],
        }
        for row in _feedback_rows()
    ]


@app.post("/api/feedback/undo")
def undo_feedback():
    with _db_lock:
        with _db_connection() as connection:
            row = connection.execute("SELECT * FROM feedback ORDER BY id DESC LIMIT 1").fetchone()
            if row is None:
                return {"success": False, "new_temperature": engine.temperature, "removed": None, "total_logs": 0}
            connection.execute("DELETE FROM feedback WHERE id = ?", (row["id"],))
        rows = _feedback_rows()
        _restore_engine(rows)
        removed = {
            "frame_index": row["frame_index"],
            "action": row["action"],
            "override_label": row["override_label"],
            "model_confidence": row["model_confidence"],
            "temperature": row["temperature"],
            "timestamp": row["ts"],
        }
        return {
            "success": True,
            "new_temperature": engine.temperature,
            "removed": removed,
            "total_logs": len(rows),
        }

# Mount static frontend build if it exists
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static_frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    def frontend_missing():
        return "<html><body>run cd frontend &amp;&amp; npm install &amp;&amp; npm run build.</body></html>"


_restore_engine(_feedback_rows())
