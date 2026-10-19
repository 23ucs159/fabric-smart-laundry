"""VALIDATE: schema + value checks. Produces one issue list per row (never silently drops data)."""
import re

import pandas as pd

from app.services.etl.transform import normalise_fabric, parse_temperature
from app.services.recommendation import load_rules

REQUIRED_COLUMNS = ["record_id", "fabric_type", "image_filename", "washing_temperature", "washing_mode",
                    "drying_method", "ironing_temperature", "label_source", "collected_at"]
OPTIONAL_FILLABLE = ["washing_temperature", "washing_mode", "drying_method", "ironing_temperature"]
VALID_IRONING = {"low", "medium", "high", "none"}
FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,80}\.(jpg|jpeg|png|webp)$", re.IGNORECASE)


def schema_errors(df: pd.DataFrame) -> list[str]:
    return [f"missing_column:{c}" for c in REQUIRED_COLUMNS if c not in df.columns]


def validate_records(df: pd.DataFrame) -> pd.DataFrame:
    """Return df plus an `issues` column (list of issue codes). Rows with *blocking* issues are invalid."""
    missing_cols = schema_errors(df)
    if missing_cols:
        raise ValueError("Schema validation failed: " + ", ".join(missing_cols))
    valid_fabrics = set(load_rules().keys())
    out = df.copy()
    issues: list[list[str]] = []
    seen_ids: set[str] = set()
    for _, r in out.iterrows():
        row_issues: list[str] = []
        rid = str(r["record_id"]).strip()
        if not rid:
            row_issues.append("missing_record_id")
        elif rid in seen_ids:
            row_issues.append("duplicate_record_id")
        seen_ids.add(rid)

        fabric_raw = str(r["fabric_type"]).strip()
        if not fabric_raw:
            row_issues.append("missing_label")
        elif normalise_fabric(fabric_raw) not in valid_fabrics:
            row_issues.append("invalid_fabric_type")

        if not FILENAME_RE.match(str(r["image_filename"]).strip()):
            row_issues.append("malformed_filename")

        t_raw = str(r["washing_temperature"]).strip()
        if not t_raw:
            row_issues.append("missing_value:washing_temperature")
        else:
            t = parse_temperature(t_raw)
            if t is None or not (0 <= t <= 95):
                row_issues.append("invalid_temperature")
        for col in ("washing_mode", "drying_method", "ironing_temperature"):
            if not str(r[col]).strip():
                row_issues.append(f"missing_value:{col}")
        iron = str(r["ironing_temperature"]).strip().lower()
        if iron and iron not in VALID_IRONING:
            row_issues.append("invalid_ironing")
        if pd.isna(pd.to_datetime(str(r["collected_at"]), errors="coerce", format="%Y-%m-%d")):
            row_issues.append("invalid_date")
        issues.append(row_issues)
    out["issues"] = issues
    return out


BLOCKING = {"missing_record_id", "duplicate_record_id", "missing_label", "invalid_fabric_type",
            "malformed_filename", "invalid_temperature", "invalid_ironing", "invalid_date"}


def is_blocking(issue_list: list[str]) -> bool:
    return any(i in BLOCKING for i in issue_list)
