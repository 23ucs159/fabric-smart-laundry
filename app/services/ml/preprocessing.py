"""Image preprocessing: orientation fix, centre-crop, resize, normalise to float32 [0, 1]."""
import io

import numpy as np
from PIL import Image, ImageFilter, ImageOps

IMG_SIZE = (128, 128)


def to_rgb(img: Image.Image) -> Image.Image:
    return ImageOps.exif_transpose(img).convert("RGB")


def preprocess_image(img: Image.Image, size: tuple[int, int] = IMG_SIZE, denoise: bool = False) -> np.ndarray:
    """Return an HxWx3 float32 array in [0, 1].

    Denoising is optional and OFF by default because fabric classification relies on fine texture.
    """
    img = to_rgb(img)
    w, h = img.size
    s = min(w, h)
    img = img.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    img = img.resize(size, Image.Resampling.LANCZOS)
    if denoise:
        img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    return np.asarray(img, dtype=np.float32) / 255.0


def open_image_bytes(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img
