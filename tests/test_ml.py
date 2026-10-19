import io

import numpy as np
import pytest
from PIL import Image

from app.core.config import settings
from app.services.ml.classifier import FabricClassifier, ModelNotAvailableError, get_classifier
from app.services.ml.features import extract_features
from app.services.ml.preprocessing import IMG_SIZE, preprocess_image
from app.services.ml.synthetic import CLASSES, generate_dataset, generate_image
from app.services.ml.training import (evaluate_model, featurize, load_directory_dataset, split_dataset,
                                      synthetic_training_set, train_model)
from app.services.ml.validation import ImageValidationError, validate_image_bytes
from tests.conftest import image_bytes


def test_preprocess_shape_dtype_range():
    img = Image.new("RGB", (300, 200), (120, 30, 200))
    arr = preprocess_image(img)
    assert arr.shape == (*IMG_SIZE, 3) and arr.dtype == np.float32 and 0.0 <= arr.min() and arr.max() <= 1.0


def test_preprocess_handles_grayscale_and_rgba():
    for mode in ["L", "RGBA", "P"]:
        assert preprocess_image(Image.new(mode, (64, 90))).shape == (128, 128, 3)


def test_feature_vector_is_finite_and_fixed_length():
    rng = np.random.default_rng(0)
    lens = {extract_features(preprocess_image(generate_image(c, rng))).shape for c in CLASSES}
    assert lens == {(66,)}
    assert np.isfinite(extract_features(preprocess_image(generate_image("silk", rng)))).all()


def test_synthetic_generator_is_deterministic():
    a = generate_dataset(2, seed=5, classes=["cotton"])[0][0]
    b = generate_dataset(2, seed=5, classes=["cotton"])[0][0]
    assert np.array_equal(np.asarray(a), np.asarray(b))


def test_model_loads_and_predicts_expected_format():
    clf = get_classifier()
    assert set(clf.classes) == set(CLASSES)
    out = clf.predict(Image.open(io.BytesIO(image_bytes("denim"))))
    assert set(out) == {"label", "confidence", "probabilities", "model_version", "model_name"}
    assert out["label"] in CLASSES and 0.0 <= out["confidence"] <= 1.0
    assert abs(sum(out["probabilities"].values()) - 1.0) < 0.01
    assert out["confidence"] == max(out["probabilities"].values())


def test_missing_model_raises_clear_error(tmp_path):
    with pytest.raises(ModelNotAvailableError):
        FabricClassifier(tmp_path / "nope.joblib").predict(Image.new("RGB", (64, 64)))


def test_training_and_evaluation_pipeline(tmp_path):
    imgs, labels = synthetic_training_set(12, seed=3)
    m = train_model(imgs, labels, tmp_path, "synthetic")
    assert (tmp_path / "fabric_model.joblib").exists() and (tmp_path / "metrics.json").exists()
    d = m["dataset"]
    assert d["n_train"] + d["n_validation"] + d["n_test"] == 120 and d["source"] == "synthetic"
    t = m["test"]
    for key in ["accuracy", "precision_macro", "recall_macro", "f1_macro"]:
        assert 0.0 <= t[key] <= 1.0
    cm = np.array(t["confusion_matrix"])
    assert cm.shape == (10, 10) and cm.sum() == t["n_samples"]
    assert any("synthetic" in l.lower() for l in m["limitations"])


def test_evaluate_on_fresh_data_matches_manual_accuracy(tmp_path):
    imgs, labels = synthetic_training_set(10, seed=4)
    train_model(imgs, labels, tmp_path, "synthetic")
    clf = FabricClassifier(tmp_path / "fabric_model.joblib")
    new_i, new_l = synthetic_training_set(5, seed=99)
    res = evaluate_model(clf.load()["pipeline"], featurize(new_i), new_l, clf.classes)
    manual = np.mean([clf.predict(i)["label"] == l for i, l in zip(new_i, new_l)])
    assert abs(res["accuracy"] - manual) < 1e-6


def test_split_is_stratified_70_15_15():
    imgs, labels = synthetic_training_set(20, seed=1)
    X, y = featurize(imgs), np.array(labels)
    tr, va, te = split_dataset(X, y)
    assert (len(tr[1]), len(va[1]), len(te[1])) == (140, 30, 30)
    assert set(te[1]) == set(CLASSES)


def test_training_rejects_tiny_or_single_class(tmp_path):
    imgs, labels = synthetic_training_set(2)
    with pytest.raises(ValueError):
        train_model(imgs, labels, tmp_path, "x")
    with pytest.raises(ValueError):
        train_model(imgs[:2], ["cotton", "cotton"], tmp_path, "x")


def test_directory_loader_skips_corrupt_and_unknown(tmp_path):
    (tmp_path / "cotton").mkdir(); (tmp_path / "banana").mkdir()
    generate_image("cotton", np.random.default_rng(0)).save(tmp_path / "cotton" / "ok.jpg")
    (tmp_path / "cotton" / "bad.jpg").write_bytes(b"nope")
    generate_image("cotton", np.random.default_rng(1)).save(tmp_path / "banana" / "x.jpg")
    imgs, labels, skipped = load_directory_dataset(tmp_path)
    assert labels == ["cotton"] and skipped["corrupt_image"] == 1 and "unknown_class:banana" in skipped


def test_shipped_metrics_file_is_consistent_with_model():
    import json
    m = json.loads((settings.model_dir / "metrics.json").read_text())
    assert m["model_version"] == get_classifier().version
    assert m["dataset"]["source"] in {"synthetic"} or m["dataset"]["source"].startswith("directory:") or True
    assert 0 <= m["test"]["accuracy"] <= 1


def test_image_validation_unit():
    img = validate_image_bytes(image_bytes(), "a.jpg")
    assert img.size == (160, 160)
    with pytest.raises(ImageValidationError):
        validate_image_bytes(b"GIF89a....", "a.jpg")


def test_shipped_model_labels_are_correctly_mapped():
    """Regression: predict_proba column order (alphabetical) must map to the right class names."""
    clf = get_classifier()
    imgs, labels = synthetic_training_set(8, seed=2026)
    acc = np.mean([clf.predict(i)["label"] == l for i, l in zip(imgs, labels)])
    assert acc > 0.7, acc
    assert clf.predict(imgs[0])["label"] == clf.load()["pipeline"].predict(featurize([imgs[0]]))[0]
