"""Fabric classifier wrapper: loads the trained scikit-learn bundle and returns probabilities."""
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from PIL import Image

from app.core.config import settings
from app.services.ml.features import extract_features
from app.services.ml.preprocessing import preprocess_image


class ModelNotAvailableError(RuntimeError):
    pass


def model_path() -> Path:
    return settings.model_dir / "fabric_model.joblib"


class FabricClassifier:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else model_path()
        self._bundle = None

    def load(self):
        if self._bundle is None:
            if not self.path.exists():
                raise ModelNotAvailableError(
                    "No trained model found. Run `python -m ml.train --synthetic 150` (or train on your dataset).")
            try:
                self._bundle = joblib.load(self.path)
            except Exception as exc:  # e.g. scikit-learn version mismatch
                raise ModelNotAvailableError(
                    f"Model file could not be loaded ({type(exc).__name__}). Retrain with `python -m ml.train --synthetic 150`.")
        return self._bundle

    @property
    def classes(self) -> list[str]:
        return list(self.load()["classes"])

    @property
    def version(self) -> str:
        return self.load()["version"]

    def predict_array(self, arr: np.ndarray) -> dict:
        b = self.load()
        pipe = b["pipeline"]
        proba = pipe.predict_proba(extract_features(arr)[None, :])[0]
        names = [str(c) for c in pipe.classes_]  # predict_proba columns follow the estimator's own class order
        order = np.argsort(proba)[::-1]
        return {
            "label": names[int(order[0])],
            "confidence": float(proba[order[0]]),
            "probabilities": {names[int(i)]: round(float(proba[i]), 4) for i in order},
            "model_version": b["version"],
            "model_name": b["model_name"],
        }

    def predict(self, img: Image.Image) -> dict:
        return self.predict_array(preprocess_image(img))


@lru_cache
def get_classifier() -> FabricClassifier:
    return FabricClassifier()
