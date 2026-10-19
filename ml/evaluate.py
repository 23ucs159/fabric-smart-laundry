"""Evaluate the saved model on a NEW dataset (fresh synthetic seed or a directory of images)."""
import argparse
import json
from pathlib import Path

import joblib

from app.core.config import settings
from app.services.ml.training import evaluate_model, featurize, load_directory_dataset, synthetic_training_set


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path)
    ap.add_argument("--synthetic", type=int, metavar="N")
    ap.add_argument("--seed", type=int, default=777, help="seed for fresh synthetic data (differs from training)")
    a = ap.parse_args()
    bundle = joblib.load(settings.model_dir / "fabric_model.joblib")
    if a.data_dir:
        images, labels, _ = load_directory_dataset(a.data_dir)
    elif a.synthetic:
        images, labels = synthetic_training_set(a.synthetic, a.seed)
    else:
        ap.error("provide --data-dir or --synthetic N")
    res = evaluate_model(bundle["pipeline"], featurize(images), labels, bundle["classes"])
    print(json.dumps({k: v for k, v in res.items() if k != "per_class"}, indent=2))


if __name__ == "__main__":
    main()
