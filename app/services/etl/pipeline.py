"""Extract -> Validate -> Transform -> Load orchestration (pandas)."""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.model_selection import train_test_split

from app.core.config import settings
from app.services.etl import extract, quality, transform, validate
from app.services.ml.preprocessing import preprocess_image
from app.services.recommendation import fabric_keys

MISSING_COLS = ["fabric_type", "washing_temperature", "washing_mode", "drying_method", "ironing_temperature"]


def _image_preprocessing(img_dir: Path, img_df: pd.DataFrame):
    ok = img_df[img_df["ok"]] if not img_df.empty else img_df
    if ok.empty:
        return None, None
    paths = [(r.fabric_class, r.filename) for r in ok.itertuples()]
    labels = [c for c, _ in paths]
    split = None
    if min(Counter(labels).values()) >= 3 and len(paths) >= 12:
        tr, te = train_test_split(range(len(paths)), test_size=0.30, stratify=labels, random_state=42)
        try:
            va, te2 = train_test_split(te, test_size=0.5, stratify=[labels[i] for i in te], random_state=42)
        except ValueError:  # too few samples per class for a second stratified split
            va, te2 = train_test_split(te, test_size=0.5, random_state=42)
        split = {"train": len(tr), "validation": len(va), "test": len(te2)}
    sample = paths[:: max(1, len(paths) // 40)]
    arrs = []
    for c, f in sample:
        with Image.open(img_dir / c / f) as im:
            arrs.append(preprocess_image(im))
    stack = np.stack(arrs)
    norm = {"target_size": "128x128", "range": "[0,1] float32", "sample_size": len(arrs),
            "channel_mean": [round(float(v), 4) for v in stack.mean(axis=(0, 1, 2))],
            "channel_std": [round(float(v), 4) for v in stack.std(axis=(0, 1, 2))]}
    return split, norm


def run_pipeline(source: Path | None = None, image_dir: Path | None = None, processed_dir: Path | None = None,
                 db=None) -> dict:
    source = Path(source or settings.raw_dir / "fabric_records.csv")
    image_dir = Path(image_dir or settings.raw_dir / "fabric_images")
    processed_dir = Path(processed_dir or settings.processed_dir)
    steps = []

    # 1. EXTRACT
    raw = extract.read_records(source)
    img_df = extract.scan_images(image_dir)
    steps.append({"name": "Extract", "status": "done", "detail": f"{len(raw)} records, {len(img_df)} image files"})

    # 2. VALIDATE
    validated = validate.validate_records(raw)
    issue_counts = Counter(i for lst in validated["issues"] for i in lst)
    blocking = validated["issues"].map(validate.is_blocking)
    invalid_df = validated[blocking]
    steps.append({"name": "Validate", "status": "done",
                  "detail": f"{int(blocking.sum())} invalid rows, {sum(issue_counts.values())} issues"})

    # missing-value inventory (raw)
    missing = {c: int((raw[c].astype(str).str.strip() == "").sum()) for c in MISSING_COLS}

    # 3. TRANSFORM
    good = validated[~blocking].copy()
    good["fabric_type"] = good["fabric_type"].map(transform.normalise_fabric)
    good, n_dups = transform.drop_duplicates(good)
    clean = transform.transform(good)
    imputed = clean.attrs.get("imputed_values", 0)
    split, norm = _image_preprocessing(image_dir, img_df)
    steps.append({"name": "Transform", "status": "done",
                  "detail": f"{n_dups} duplicates removed, {imputed} values imputed, encoded + normalised"})

    # 4. LOAD
    processed_dir.mkdir(parents=True, exist_ok=True)
    clean.to_csv(processed_dir / "fabric_records_clean.csv", index=False)
    invalid_df.drop(columns=[], errors="ignore").assign(issues=invalid_df["issues"].map(lambda x: ";".join(x))) \
        .to_csv(processed_dir / "fabric_records_rejected.csv", index=False)
    steps.append({"name": "Load", "status": "done",
                  "detail": f"{len(clean)} clean rows written to {processed_dir.name}/fabric_records_clean.csv"})

    dup_ids = int(issue_counts.get("duplicate_record_id", 0))
    report = quality.build_report(
        source=source.name, total=len(raw), valid=len(clean), invalid=int(blocking.sum()),
        duplicates=n_dups + dup_ids, missing_values=missing, imputed=imputed,
        issue_counts=dict(issue_counts),
        class_distribution={k: int(v) for k, v in Counter(clean["fabric_type"]).items()},
        supported=fabric_keys(),
        invalid_samples=[{"record_id": str(r.record_id), "fabric_type": str(r.fabric_type),
                          "image_filename": str(r.image_filename), "issues": list(r.issues)}
                         for r in invalid_df.head(15).itertuples()],
        images=quality.image_summary(img_df, split, norm), steps=steps)
    (processed_dir / "quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    if db is not None:
        from app.models import EtlRun
        db.add(EtlRun(source=source.name, status="completed", report_json=json.dumps(report)))
        db.commit()
    return report
