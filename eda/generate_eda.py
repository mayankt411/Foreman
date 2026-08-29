import os, json, sys
sys.path.insert(0, '.')
from src.severity import compute_severity

data_index_path = os.path.join('data', 'pcb_defects', 'dataset_index.json')
with open(data_index_path, 'r', encoding='utf-8') as f:
    records = json.load(f)

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import nbformat as nbf

df = pd.DataFrame(records)
df['severity_score'] = [compute_severity(r['primary_label'], r['area_ratio']) for _, r in df.iterrows()]

os.makedirs('eda', exist_ok=True)

# 1. Class Distribution Plot
plt.figure(figsize=(9, 5), dpi=150)
class_counts = df['primary_label'].value_counts()
colors = ['#e74c3c', '#e67e22', '#f1c40f', '#3498db', '#2ecc71']
bars = plt.bar(class_counts.index, class_counts.values, color=colors[:len(class_counts)])
plt.title('PCB Surface Defect Class Distribution (Dataset Ground Truth)', fontsize=13, fontweight='bold')
plt.xlabel('Defect / Quality Class', fontsize=11)
plt.ylabel('Number of Images', fontsize=11)
plt.grid(axis='y', linestyle='--', alpha=0.6)
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2.0, yval + 1, str(int(yval)), ha='center', va='bottom', fontweight='bold')
plt.tight_layout()
plt.savefig('eda/class_distribution.png')
plt.close()

# 2. Defect Area Ratio Distribution
plt.figure(figsize=(9, 5), dpi=150)
plt.hist(df[df['area_ratio'] > 0]['area_ratio'] * 100, bins=20, color='#34495e', edgecolor='white')
plt.title('Defect Area as % of Total Image Area (Physical Footprint)', fontsize=13, fontweight='bold')
plt.xlabel('Defect Area (%)', fontsize=11)
plt.ylabel('Frequency (Defective Images)', fontsize=11)
plt.grid(axis='y', linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig('eda/defect_area_distribution.png')
plt.close()

# 3. Severity Distribution
plt.figure(figsize=(9, 5), dpi=150)
for lbl, group in df.groupby('primary_label'):
    plt.hist(group['severity_score'], bins=15, alpha=0.6, label=lbl)
plt.title('Empirical Defect Severity Score S(c) Distribution', fontsize=13, fontweight='bold')
plt.xlabel('Severity Score S(c) [0.0 - 1.0]', fontsize=11)
plt.ylabel('Image Count', fontsize=11)
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig('eda/severity_distribution.png')
plt.close()

# 4. Sample Grid with Bounding Box overlays
unique_classes = df['primary_label'].unique()
fig, axes = plt.subplots(1, len(unique_classes), figsize=(4 * len(unique_classes), 4), dpi=150)
if len(unique_classes) == 1:
    axes = [axes]

for ax, cls in zip(axes, unique_classes):
    sample = df[df['primary_label'] == cls].iloc[0]
    img = Image.open(sample['file_path']).convert('RGB')
    ax.imshow(img)
    score_str = str(round(sample['severity_score'], 2))
    ax.set_title(cls + '\nS(c)=' + score_str, fontsize=10, fontweight='bold')
    ax.axis('off')
    for bbox in sample['bboxes']:
        rect = patches.Rectangle((bbox[0], bbox[1]), bbox[2], bbox[3], linewidth=2, edgecolor='red', facecolor='none')
        ax.add_patch(rect)

plt.tight_layout()
plt.savefig('eda/sample_inspections_grid.png')
plt.close()

# 5. Build eda/01_eda.ipynb Jupyter Notebook
nb = nbf.v4.new_notebook()
cells = [
    nbf.v4.new_markdown_cell('# XiVLM-Loop: Phase 1 -- Exploratory Data Analysis & Severity Grounding\n\nThis notebook performs empirical exploratory data analysis on the industrial PCB defect dataset, computes physical defect severity distributions S(c), and analyzes class balance and false-negative implications.'),
    nbf.v4.new_code_cell('import os, json\nimport pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\nimport matplotlib.patches as patches\nfrom PIL import Image\n\nfrom src.severity import compute_severity, CLASS_SEVERITY_TIERS\n\ndata_index_path = os.path.join("..", "data", "pcb_defects", "dataset_index.json")\nwith open(data_index_path, "r", encoding="utf-8") as f:\n    records = json.load(f)\n\ndf = pd.DataFrame(records)\ndf["severity_score"] = [compute_severity(row["primary_label"], row["area_ratio"]) for _, row in df.iterrows()]\ndf.head()'),
    nbf.v4.new_markdown_cell('## 1. Class Balance & Resolution Statistics'),
    nbf.v4.new_code_cell('print("Total Images:", len(df))\nprint("Resolution:", df["width"].iloc[0], "x", df["height"].iloc[0])\nprint("Channels: 3 (RGB)")\nprint("\\nClass Breakdown:")\nprint(df["primary_label"].value_counts())\nprint("\\nSplit Breakdown:")\nprint(df["split"].value_counts())'),
    nbf.v4.new_markdown_cell('## 2. Defect Size & Severity Distribution\n\nDefect severity S(c) is parameterized by industrial risk tier and scaled by defect footprint percentage.'),
    nbf.v4.new_code_cell('df.groupby("primary_label")[["area_ratio", "severity_score"]].describe()'),
    nbf.v4.new_markdown_cell('## 3. Data Quality & Imbalance Analysis\n\n- **Class Imbalance**: High-severity defects such as `short_circuit` and `pcb_damage` carry high penalty costs in edge electronics manufacturing. Uncalibrated VLMs tend to suffer higher false-negative rates on subtle solder joint anomalies (`dry_joint`).\n- **Ambiguous Boundaries**: Incomplete solder wetting creates non-convex polygons where bounding boxes capture high background noise, motivating the multi-modal Faithfulness Guard in Phase 3.')
]

nb['cells'] = cells
with open(os.path.join('eda', '01_eda.ipynb'), 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print('EDA Notebook & Plots generated successfully.')
