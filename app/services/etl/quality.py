"""Data-quality report builder."""
from collections import Counter
from datetime import datetime, timezone

import pandas as pd


def image_summary(img_df: pd.DataFrame, split: dict | None, norm: dict | None) -> dict:
    if img_df.empty:
        return {"scanned": 0, "valid": 0, "corrupted": 0, "dimensions": None, "class_distribution": {},
                "split": None, "normalisation": None}
    ok = img_df[img_df["ok"]]
    dims = None
    if not ok.empty:
        dims = {"min": f"{int(ok.width.min())}x{int(ok.height.min())}", "max": f"{int(ok.width.max())}x{int(ok.height.max())}",
                "mean": f"{ok.width.mean():.0f}x{ok.height.mean():.0f}"}
    return {
        "scanned": int(len(img_df)), "valid": int(len(ok)), "corrupted": int((img_df["error"] == "corrupted_file").sum()),
        "unknown_class_folder": int((img_df["error"] == "unknown_class_folder").sum()),
        "dimensions": dims,
        "class_distribution": {k: int(v) for k, v in Counter(ok["fabric_class"]).items()},
        "split": split, "normalisation": norm,
    }


def build_report(*, source: str, total: int, valid: int, invalid: int, duplicates: int, missing_values: dict,
                 imputed: int, issue_counts: dict, class_distribution: dict, supported: list[str],
                 invalid_samples: list[dict], images: dict, steps: list[dict]) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "status": "completed",
        "records": {"total": total, "valid": valid, "invalid": invalid, "duplicates": duplicates,
                    "missing_values": missing_values, "missing_values_total": int(sum(missing_values.values())),
                    "imputed_values": imputed},
        "issue_counts": issue_counts,
        "supported_fabric_categories": supported,
        "class_distribution": class_distribution,
        "invalid_samples": invalid_samples,
        "images": images,
        "steps": steps,
    }
