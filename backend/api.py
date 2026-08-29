import os
import sys
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd

app = FastAPI(title="XiVLM-Loop Telemetry & Inspection API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "pcb_defects")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

# Load dataset index if available to enrich predictions with exact bounding boxes
dataset_index_map = {}
dataset_index_path = os.path.join(DATA_DIR, "dataset_index.json")
if os.path.exists(dataset_index_path):
    try:
        with open(dataset_index_path, "r", encoding="utf-8") as f:
            idx_list = json.load(f)
            for item in idx_list:
                fname = item.get("file_name") or os.path.basename(item.get("file_path", ""))
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
        "device": "ARM64 / CPU",
        "version": "2.1.0"
    }

@app.get("/api/metrics")
def get_metrics():
    metrics_path = os.path.join(RESULTS_DIR, "metrics_summary.json")
    if not os.path.exists(metrics_path):
        raise HTTPException(status_code=404, detail="Metrics summary not found")
    with open(metrics_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/predictions")
def get_predictions():
    csv_path = os.path.join(RESULTS_DIR, "predictions.csv")
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Predictions not found")
    df = pd.read_csv(csv_path)
    records = []
    for idx, row in df.iterrows():
        item = row.to_dict()
        file_path = str(row.get("file_path", ""))
        fname = os.path.basename(file_path)
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
        records.append(item)
    return records

@app.get("/api/image/{idx}")
def get_image(idx: int):
    csv_path = os.path.join(RESULTS_DIR, "predictions.csv")
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Predictions CSV not found")
    df = pd.read_csv(csv_path)
    if idx < 0 or idx >= len(df):
        raise HTTPException(status_code=404, detail="Frame index out of bounds")
    
    file_path = str(df.iloc[idx]["file_path"])
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/jpeg")
    
    # Fallback to searching in train/test
    fname = os.path.basename(file_path)
    for sub in ["test", "train"]:
        alt_path = os.path.join(DATA_DIR, sub, fname)
        if os.path.exists(alt_path):
            return FileResponse(alt_path, media_type="image/jpeg")
            
    raise HTTPException(status_code=404, detail=f"Image file not found: {fname}")

class FeedbackPayload(BaseModel):
    frame_index: int
    action: str
    override_label: str = ""
    current_temperature: float = 0.564

operator_logs = []

@app.post("/api/feedback")
def post_feedback(payload: FeedbackPayload):
    new_t = payload.current_temperature
    if payload.action == "accept":
        new_t = max(0.10, round(payload.current_temperature - 0.02, 3))
    elif payload.action == "overrule":
        new_t = min(2.0, round(payload.current_temperature + 0.04, 3))
    
    log_entry = {
        "frame_index": payload.frame_index,
        "action": payload.action,
        "override_label": payload.override_label,
        "temperature": new_t,
        "timestamp": pd.Timestamp.now().strftime("%H:%M:%S.%f")[:-3]
    }
    operator_logs.append(log_entry)
    return {"success": True, "new_temperature": new_t, "log": log_entry, "total_logs": len(operator_logs)}

@app.get("/api/feedback/history")
def get_feedback_history():
    return operator_logs

# Mount static frontend build if it exists
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static_frontend")