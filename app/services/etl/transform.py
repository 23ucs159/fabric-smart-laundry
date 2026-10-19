"""TRANSFORM: clean, de-duplicate, impute, encode and normalise."""
import re

import pandas as pd

from app.services.recommendation import load_rules


def normalise_fabric(value: str) -> str:
    v = str(value).strip().lower()
    for key, r in load_rules().items():
        if v == key or v in r.get("aliases", []):
            return key
    return v


def parse_temperature(value) -> float | None:
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*(?:°\s*c|c)?\s*", str(value), re.IGNORECASE)
    return float(m.group(1)) if m else None


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Input: validated frame (with `issues`) restricted to non-blocking rows."""
    rules = load_rules()
    out = df.copy()
    out["fabric_type"] = out["fabric_type"].map(normalise_fabric)
    out["image_filename"] = out["image_filename"].str.strip()
    out["washing_temperature"] = out["washing_temperature"].map(parse_temperature)
    out["ironing_temperature"] = out["ironing_temperature"].str.strip().str.lower()
    out["washing_mode"] = out["washing_mode"].str.strip()
    out["drying_method"] = out["drying_method"].str.strip()

    # impute missing optional values from the knowledge base (documented, counted in the report)
    imputed = 0
    for idx, r in out.iterrows():
        rule = rules[r["fabric_type"]]
        if pd.isna(r["washing_temperature"]):
            out.at[idx, "washing_temperature"] = float(rule["max_temp_c"]); imputed += 1
        if not r["washing_mode"]:
            out.at[idx, "washing_mode"] = rule["wash_modes"][0]; imputed += 1
        if not r["drying_method"]:
            out.at[idx, "drying_method"] = rule["drying_method"].split(" or ")[0]; imputed += 1
        if not r["ironing_temperature"]:
            out.at[idx, "ironing_temperature"] = "low"; imputed += 1
    out.attrs["imputed_values"] = imputed

    # encoding + normalisation
    classes = sorted(rules.keys())
    out["fabric_code"] = out["fabric_type"].map({c: i for i, c in enumerate(classes)})
    t = out["washing_temperature"].astype(float)
    out["temp_norm"] = ((t - 0) / (95 - 0)).round(4)  # min-max over the valid range 0..95
    out["ironing_code"] = out["ironing_temperature"].map({"none": 0, "low": 1, "medium": 2, "high": 3})
    return out.drop(columns=["issues"], errors="ignore")


def drop_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Duplicates = same (normalised fabric, filename). First occurrence wins."""
    key = df["fabric_type"].map(normalise_fabric) + "|" + df["image_filename"].str.strip().str.lower()
    dup_mask = key.duplicated(keep="first")
    return df[~dup_mask], int(dup_mask.sum())
