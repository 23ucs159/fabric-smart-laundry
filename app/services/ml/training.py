"""Training / evaluation pipeline shared by ml/train.py, ml/evaluate.py and the tests."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.services.ml.features import extract_features
from app.services.ml.preprocessing import preprocess_image
from app.services.ml.synthetic import CLASSES, generate_dataset

MODEL_NAME = "StandardScaler + RandomForest (colour/texture features)"

LIMITATIONS = [
    "Classical machine-learning baseline using hand-crafted colour and texture features, not a deep CNN.",
    "Metrics are measured on a held-out split of the dataset named in 'dataset.source' only.",
    "If the source is 'synthetic', the images are procedurally generated textures, NOT real fabric photographs; "
    "the numbers do not predict real-world accuracy. Train on a real labelled dataset for real use.",
    "Photographs of real garments (folds, lighting, backgrounds) differ strongly from clean texture crops.",
    "Always verify the care label before washing; predictions are advisory.",
]


def load_directory_dataset(data_dir: Path):
    """data_dir/<class_name>/*.jpg|png|webp. Corrupt files and unknown classes are skipped and counted."""
    images, labels, skipped = [], [], Counter()
    for cdir in sorted(Path(data_dir).iterdir()):
        if not cdir.is_dir():
            continue
        if cdir.name not in CLASSES:
            skipped[f"unknown_class:{cdir.name}"] += 1
            continue
        for f in sorted(cdir.iterdir()):
            if f.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            try:
                img = Image.open(f)
                img.load()
            except Exception:
                skipped["corrupt_image"] += 1
                continue
            images.append(img)
            labels.append(cdir.name)
    return images, labels, dict(skipped)


def featurize(images):
    return np.stack([extract_features(preprocess_image(i)) for i in images])


def split_dataset(X, y, seed=42):
    """Stratified 70/15/15 train/validation/test split."""
    X_tr, X_tmp, y_tr, y_tmp = train_test_split(X, y, test_size=0.30, stratify=y, random_state=seed)
    X_va, X_te, y_va, y_te = train_test_split(X_tmp, y_tmp, test_size=0.50, stratify=y_tmp, random_state=seed)
    return (X_tr, y_tr), (X_va, y_va), (X_te, y_te)


def evaluate_model(pipeline, X, y, classes) -> dict:
    pred = pipeline.predict(X)
    p, r, f, _ = precision_recall_fscore_support(y, pred, labels=classes, average=None, zero_division=0)
    mp, mr, mf, _ = precision_recall_fscore_support(y, pred, labels=classes, average="macro", zero_division=0)
    return {
        "n_samples": int(len(y)),
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "precision_macro": round(float(mp), 4),
        "recall_macro": round(float(mr), 4),
        "f1_macro": round(float(mf), 4),
        "per_class": {c: {"precision": round(float(p[i]), 4), "recall": round(float(r[i]), 4),
                          "f1": round(float(f[i]), 4)} for i, c in enumerate(classes)},
        "confusion_matrix": confusion_matrix(y, pred, labels=classes).tolist(),
        "labels": list(classes),
    }


def train_model(images, labels, out_dir: Path, source: str, seed: int = 42, skipped: dict | None = None) -> dict:
    if len(set(labels)) < 2:
        raise ValueError("Need at least two classes to train.")
    counts = Counter(labels)
    if min(counts.values()) < 4:
        raise ValueError("Each class needs at least 4 images for a stratified split.")
    X = featurize(images)
    y = np.array(labels)
    (X_tr, y_tr), (X_va, y_va), (X_te, y_te) = split_dataset(X, y, seed)
    classes = sorted(set(labels), key=lambda c: CLASSES.index(c) if c in CLASSES else 99)
    pipe = Pipeline([("scale", StandardScaler()),
                     ("rf", RandomForestClassifier(n_estimators=300, random_state=seed, n_jobs=-1))])
    pipe.fit(X_tr, y_tr)
    version = "rf-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    metrics = {
        "model_name": MODEL_NAME,
        "model_version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "classes": classes,
        "dataset": {"source": source, "seed": seed, "per_class_counts": dict(counts),
                    "n_train": int(len(y_tr)), "n_validation": int(len(y_va)), "n_test": int(len(y_te)),
                    "skipped": skipped or {}},
        "validation": evaluate_model(pipe, X_va, y_va, classes),
        "test": evaluate_model(pipe, X_te, y_te, classes),
        "limitations": LIMITATIONS,
    }
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipe, "classes": classes, "version": version, "model_name": MODEL_NAME}, out_dir / "fabric_model.joblib")
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def synthetic_training_set(n_per_class: int, seed: int = 42):
    return generate_dataset(n_per_class, seed)
