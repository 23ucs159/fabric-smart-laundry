"""Train the fabric classifier.

  python -m ml.train --synthetic 150            # procedurally generated textures (offline demo)
  python -m ml.train --data-dir data/raw/fabric_images_real   # real dataset: <dir>/<class>/*.jpg
"""
import argparse
from pathlib import Path

from app.core.config import settings
from app.services.ml.training import load_directory_dataset, synthetic_training_set, train_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, help="Folder with one sub-folder per fabric class")
    ap.add_argument("--synthetic", type=int, metavar="N", help="Generate N synthetic images per class instead")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=settings.model_dir)
    a = ap.parse_args()
    if a.synthetic:
        images, labels = synthetic_training_set(a.synthetic, a.seed)
        source, skipped = "synthetic", {}
    elif a.data_dir:
        images, labels, skipped = load_directory_dataset(a.data_dir)
        source = f"directory:{a.data_dir}"
    else:
        ap.error("provide --data-dir or --synthetic N")
    m = train_model(images, labels, a.out, source, a.seed, skipped)
    print(f"Saved model {m['model_version']} to {a.out}")
    print(f"Dataset source: {m['dataset']['source']}  counts: {m['dataset']['per_class_counts']}")
    print(f"Validation accuracy: {m['validation']['accuracy']}  Test accuracy: {m['test']['accuracy']}  "
          f"Macro F1: {m['test']['f1_macro']}")


if __name__ == "__main__":
    main()
