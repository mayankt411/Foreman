"""
severity.py - Defect Severity Scoring Module for XiVLM-Loop
"""
import json, os
from typing import Dict, Any, Optional

CLASS_SEVERITY_TIERS = {
    "short_circuit": {"base_severity": 0.90, "criticality": "Critical", "description": "Direct electrical short circuit / solder bridge."},
    "pcb_damage": {"base_severity": 0.80, "criticality": "High", "description": "Physical substrate cracking, copper trace fracture."},
    "incorrect_installation": {"base_severity": 0.70, "criticality": "Medium-High", "description": "Component polarity inversion or misplacement."},
    "dry_joint": {"base_severity": 0.60, "criticality": "Medium", "description": "Insufficient solder wetting, cold solder joint."},
    "normal": {"base_severity": 0.05, "criticality": "Negligible", "description": "Compliant board surface."}
}

REFERENCE_AREA_RATIO = 0.05

def compute_severity(defect_class: str, area_ratio: Optional[float] = None) -> float:
    cls_clean = str(defect_class).lower().strip().replace(' ', '_')
    if cls_clean not in CLASS_SEVERITY_TIERS:
        if 'short' in cls_clean or 'bridge' in cls_clean:
            cls_clean = 'short_circuit'
        elif 'damage' in cls_clean or 'crack' in cls_clean or 'scratch' in cls_clean:
            cls_clean = 'pcb_damage'
        elif 'install' in cls_clean or 'misplaced' in cls_clean or 'orient' in cls_clean:
            cls_clean = 'incorrect_installation'
        elif 'joint' in cls_clean or 'solder' in cls_clean or 'pinhole' in cls_clean:
            cls_clean = 'dry_joint'
        else:
            cls_clean = 'normal'
    base_sev = CLASS_SEVERITY_TIERS[cls_clean]["base_severity"]
    if area_ratio is None or area_ratio <= 0:
        return float(round(base_sev, 4))
    area_factor = min(1.0, area_ratio / REFERENCE_AREA_RATIO)
    scaled_sev = base_sev * (0.8 + 0.2 * area_factor)
    return float(round(min(1.0, max(0.0, scaled_sev)), 4))

def export_severity_map(filepath: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    payload = {
        "class_severity_tiers": CLASS_SEVERITY_TIERS,
        "reference_area_ratio": REFERENCE_AREA_RATIO,
        "formula": "S(c, area_ratio) = S_base(c) * (0.8 + 0.2 * min(1.0, area_ratio / REFERENCE_AREA_RATIO))"
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

if __name__ == '__main__':
    map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'severity_map.json')
    export_severity_map(map_path)
    print(f'Severity map exported to {map_path}')
    for cls in CLASS_SEVERITY_TIERS.keys():
        print(f'  {cls:25s} -> Base S(c)={compute_severity(cls):.2f}, Scaled (area=2%)={compute_severity(cls, 0.02):.2f}')
