"""Deterministic generator for raw ETL inputs + a small SAMPLE image set (synthetic textures).

Creates:
  data/raw/fabric_images/<class>/sample_XX.jpg   (6 per class, synthetic)  + one deliberately corrupt file
  data/raw/fabric_records.csv                    (baseline records, a few natural defects)
  data/raw/messy_fabric_records.csv              (deliberately messy ETL test data)
"""
import csv
import json
import random
from pathlib import Path

import numpy as np

from app.services.ml.synthetic import CLASSES, generate_image

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RULES = json.loads((ROOT / "data" / "knowledge" / "care_rules.json").read_text(encoding="utf-8"))
COLS = ["record_id", "fabric_type", "image_filename", "washing_temperature", "washing_mode",
        "drying_method", "ironing_temperature", "label_source", "collected_at"]


def iron_level(text):
    t = text.lower()
    if t.startswith("do not"):
        return "none"
    return t.split(" ")[0] if t.split(" ")[0] in {"low", "medium", "high"} else "low"


def row(i, fabric, rnd, n):
    r = RULES[fabric]
    return [f"R{i:04d}", fabric, f"{fabric}_{n:03d}.jpg", r["max_temp_c"], r["wash_modes"][0],
            r["drying_method"].split(" or ")[0], iron_level(r["ironing"]),
            rnd.choice(["manual", "supplier_label", "expert"]), f"2026-0{rnd.randint(1, 9)}-{rnd.randint(10, 28)}"]


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        w.writerows(rows)


def main():
    rng = np.random.default_rng(2024)
    for c in CLASSES:
        d = RAW / "fabric_images" / c
        d.mkdir(parents=True, exist_ok=True)
        for k in range(6):
            generate_image(c, rng).save(d / f"sample_{k:02d}.jpg", quality=88)
    (RAW / "fabric_images" / "cotton" / "corrupt_sample.jpg").write_bytes(b"not really a jpeg")

    rnd = random.Random(42)
    rows, i = [], 1
    for fabric in CLASSES:
        for n in range(1, 25):
            rows.append(row(i, fabric, rnd, n)); i += 1
    rows.append(rows[5][:]); rows[-1][0] = "R9001"          # duplicate (same file+fabric)
    rows.append(rows[40][:]); rows[-1][0] = "R9002"          # duplicate
    rows[17][3] = ""                                          # missing temperature
    rows[63][5] = ""                                          # missing drying
    rows[101][4] = ""                                         # missing washing mode
    rows[150][1] = "Cotton "                                  # needs normalisation
    write(RAW / "fabric_records.csv", rows)

    messy = [
        ["M001", "cotton", "cotton_001.jpg", "40", "Normal", "Air dry", "medium", "manual", "2026-03-11"],
        ["M002", "COTTON", "cotton_002.jpg", "40°C", "Normal", "Air dry", "medium", "manual", "2026-03-12"],
        ["M003", "silk", "silk_001.jpg", "30", "Delicate", "Air dry", "low", "expert", "2026-03-12"],
        ["M004", "silk", "silk_001.jpg", "30", "Delicate", "Air dry", "low", "expert", "2026-03-12"],   # duplicate
        ["M005", "", "wool_001.jpg", "30", "Wool", "Dry flat", "low", "manual", "2026-03-13"],          # missing label
        ["M006", "banana", "banana_001.jpg", "30", "Normal", "Air dry", "low", "manual", "2026-03-13"],  # invalid fabric
        ["M007", "polyester", "poly_001.jpg", "250", "Normal", "Air dry", "low", "manual", "2026-03-14"],  # invalid temp
        ["M008", "polyester", "poly_002.jpg", "-5", "Normal", "Air dry", "low", "manual", "2026-03-14"],   # invalid temp
        ["M009", "linen", "../../etc/passwd", "40", "Normal", "Air dry", "high", "manual", "2026-03-15"],  # malformed filename
        ["M010", "linen", "linen 001<script>.jpg", "40", "Normal", "Air dry", "high", "manual", "2026-03-15"],
        ["M011", "denim", "denim_001.jpg", "abc", "Normal", "Air dry", "high", "manual", "2026-03-16"],   # non-numeric temp
        ["M012", "denim", "denim_002.jpg", "30", "Normal", "Air dry", "scorching", "manual", "2026-03-16"],  # invalid ironing
        ["M013", "nylon", "nylon_001.gif", "30", "Gentle", "Air dry", "low", "manual", "2026-03-17"],     # bad extension
        ["M014", "rayon", "rayon_001.jpg", "", "Gentle", "", "low", "manual", "2026-03-17"],            # missing values
        ["M015", "velvet", "velvet_001.jpg", "30", "Gentle", "Air dry", "none", "manual", "not-a-date"],  # invalid date
        ["M002", "wool", "wool_002.jpg", "30", "Wool", "Dry flat", "low", "manual", "2026-03-18"],       # duplicate record_id
        ["M017", "Synthetic", "blend_001.jpg", "30", "Gentle", "Air dry", "low", "manual", "2026-03-18"],  # alias -> blended
    ]
    write(RAW / "messy_fabric_records.csv", messy)
    print("raw data written to", RAW)


if __name__ == "__main__":
    main()
