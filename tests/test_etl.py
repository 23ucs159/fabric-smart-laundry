from pathlib import Path

import pandas as pd
import pytest

from app.core.config import settings
from app.services.etl import extract, transform, validate
from app.services.etl.pipeline import run_pipeline

RAW = settings.raw_dir


def test_baseline_data_mostly_valid(tmp_path):
    r = run_pipeline(RAW / "fabric_records.csv", processed_dir=tmp_path)
    rec = r["records"]
    assert rec["total"] == 242 and rec["valid"] == 240 and rec["invalid"] == 0
    assert rec["duplicates"] == 2 and rec["missing_values_total"] == 3 and rec["imputed_values"] == 3
    assert (tmp_path / "fabric_records_clean.csv").exists() and (tmp_path / "quality_report.json").exists()
    assert set(r["class_distribution"]) == set(r["supported_fabric_categories"])


def test_messy_data_problems_detected(tmp_path):
    r = run_pipeline(RAW / "messy_fabric_records.csv", processed_dir=tmp_path)
    ic = r["issue_counts"]
    for expected in ["missing_label", "invalid_fabric_type", "invalid_temperature", "malformed_filename",
                     "invalid_ironing", "invalid_date", "duplicate_record_id"]:
        assert ic.get(expected, 0) >= 1, expected
    assert ic["invalid_temperature"] == 3 and ic["malformed_filename"] == 3
    rec = r["records"]
    assert rec["total"] == 17 and rec["valid"] == 5 and rec["invalid"] == 11 and rec["duplicates"] == 2
    assert rec["missing_values"]["fabric_type"] == 1


def test_clean_output_is_normalised(tmp_path):
    run_pipeline(RAW / "messy_fabric_records.csv", processed_dir=tmp_path)
    df = pd.read_csv(tmp_path / "fabric_records_clean.csv")
    assert set(df["fabric_type"]) <= {"cotton", "silk", "rayon", "blended"}
    assert df["washing_temperature"].between(0, 95).all() and df["temp_norm"].between(0, 1).all()
    assert df["washing_temperature"].notna().all()
    assert "blended" in set(df["fabric_type"])  # "Synthetic" alias normalised


def test_rejected_rows_written_with_reasons(tmp_path):
    run_pipeline(RAW / "messy_fabric_records.csv", processed_dir=tmp_path)
    rej = pd.read_csv(tmp_path / "fabric_records_rejected.csv")
    assert len(rej) == 11 and rej["issues"].str.len().min() > 0


def test_schema_validation_fails_on_missing_columns(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("record_id,fabric_type\nR1,cotton\n")
    with pytest.raises(ValueError, match="Schema validation failed"):
        run_pipeline(p, processed_dir=tmp_path)


def test_parse_temperature_and_normalise():
    assert transform.parse_temperature("40°C") == 40.0 and transform.parse_temperature("abc") is None
    assert transform.normalise_fabric(" Cotton ") == "cotton" and transform.normalise_fabric("Jeans") == "denim"


def test_missing_values_imputed_from_knowledge_base(tmp_path):
    p = tmp_path / "m.csv"
    p.write_text("record_id,fabric_type,image_filename,washing_temperature,washing_mode,drying_method,ironing_temperature,label_source,collected_at\n"
                 "R1,wool,wool_1.jpg,,,,,manual,2026-01-01\n")
    r = run_pipeline(p, image_dir=tmp_path / "none", processed_dir=tmp_path)
    df = pd.read_csv(tmp_path / "fabric_records_clean.csv")
    assert r["records"]["valid"] == 1 and df.loc[0, "washing_temperature"] == 30.0 and df.loc[0, "washing_mode"] == "Wool"


def test_image_scan_reports_corrupt_and_dimensions():
    df = extract.scan_images(RAW / "fabric_images")
    assert (df["error"] == "corrupted_file").sum() == 1
    assert df[df.ok].width.min() == 160 and set(df[df.ok].fabric_class) == set(
        ["cotton", "silk", "wool", "linen", "polyester", "denim", "nylon", "rayon", "velvet", "blended"])


def test_duplicate_detection():
    df = pd.DataFrame({"fabric_type": ["cotton", "Cotton", "silk"], "image_filename": ["a.jpg", "A.jpg ", "a.jpg"]})
    out, n = transform.drop_duplicates(df)
    assert n == 1 and len(out) == 2
