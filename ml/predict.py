"""Predict the fabric of one image:  python -m ml.predict path/to/image.jpg"""
import json
import sys

from PIL import Image

from app.services.ml.classifier import FabricClassifier

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m ml.predict <image>")
    print(json.dumps(FabricClassifier().predict(Image.open(sys.argv[1])), indent=2))
