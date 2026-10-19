"""EXTRACT: read raw tabular records and scan the raw image folder."""
from pathlib import Path

import pandas as pd
from PIL import Image

from app.services.ml.synthetic import CLASSES

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def read_records(path: Path) -> pd.DataFrame:
    """Everything is read as text so validation sees the raw values."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")


def scan_images(image_dir: Path) -> pd.DataFrame:
    rows = []
    image_dir = Path(image_dir)
    if not image_dir.exists():
        return pd.DataFrame(columns=["fabric_class", "filename", "ok", "width", "height", "format", "error"])
    for cdir in sorted(p for p in image_dir.iterdir() if p.is_dir()):
        for f in sorted(cdir.iterdir()):
            if f.suffix.lower() not in IMAGE_EXTS:
                continue
            rec = {"fabric_class": cdir.name, "filename": f.name, "ok": False, "width": None,
                   "height": None, "format": None, "error": None}
            if cdir.name not in CLASSES:
                rec["error"] = "unknown_class_folder"
            else:
                try:
                    with Image.open(f) as im:
                        im.verify()
                    with Image.open(f) as im:
                        rec.update(ok=True, width=im.width, height=im.height, format=im.format)
                except Exception:
                    rec["error"] = "corrupted_file"
            rows.append(rec)
    return pd.DataFrame(rows)
