"""Hand-crafted colour + texture features (CPU-only, no GPU or deep-learning framework needed)."""
import numpy as np
from PIL import Image

from app.services.ml.preprocessing import IMG_SIZE


def extract_features(arr: np.ndarray) -> np.ndarray:
    assert arr.shape[:2] == IMG_SIZE, "array must be preprocessed to IMG_SIZE"
    n = arr.shape[0] * arr.shape[1]
    u8 = (arr * 255).astype(np.uint8)
    hsv = np.asarray(Image.fromarray(u8).convert("HSV"), dtype=np.float32) / 255.0
    f: list[float] = []
    for c in range(3):
        f += [float(hsv[..., c].mean()), float(hsv[..., c].std())]
    f += list(np.histogram(hsv[..., 0], bins=8, range=(0, 1))[0] / n)
    f += list(np.histogram(hsv[..., 1], bins=4, range=(0, 1))[0] / n)
    f += list(np.histogram(hsv[..., 2], bins=4, range=(0, 1))[0] / n)

    gray = arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    f += [float(gray.mean()), float(gray.std()), float(np.percentile(gray, 5)),
          float(np.percentile(gray, 95)), float((gray > 0.9).mean())]

    gy, gx = np.gradient(gray)
    mag = np.hypot(gx, gy)
    ang = np.arctan2(gy, gx) % np.pi
    f += [float(mag.mean()), float(mag.std()), float(np.percentile(mag, 90))]
    hist, _ = np.histogram(ang, bins=8, range=(0, np.pi), weights=mag)
    f += list(hist / (hist.sum() + 1e-8))
    f.append(float(np.abs(gx).mean() / (np.abs(gy).mean() + 1e-6)))

    spec = np.abs(np.fft.fftshift(np.fft.fft2(gray - gray.mean()))) ** 2
    cy, cx = spec.shape[0] // 2, spec.shape[1] // 2
    yy, xx = np.indices(spec.shape)
    r = np.hypot(yy - cy, xx - cx)
    edges = np.linspace(0, 64, 9)
    energies = np.array([spec[(r >= a) & (r < b)].sum() for a, b in zip(edges[:-1], edges[1:])])
    total = energies.sum() + 1e-8
    f += list(energies / total) + [float(np.log10(total))]

    bs = gray.shape[0] // 16
    blocks = gray.reshape(16, bs, 16, bs).std(axis=(1, 3))
    f += [float(blocks.mean()), float(blocks.std())]

    g = gray[::2, ::2]
    c = g[1:-1, 1:-1]
    code = np.zeros_like(c, dtype=np.int32)
    offs = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]
    for k, (dy, dx) in enumerate(offs):
        nb = g[1 + dy:g.shape[0] - 1 + dy, 1 + dx:g.shape[1] - 1 + dx]
        code |= (nb >= c).astype(np.int32) << k
    f += list(np.histogram(code >> 4, bins=16, range=(0, 16))[0] / code.size)
    return np.asarray(f, dtype=np.float32)
