"""Procedurally generated fabric-like textures.

IMPORTANT: these are NOT photographs of real fabric. They exist so the full pipeline (training, evaluation,
inference) can run offline. Metrics measured on them say nothing about real-world accuracy.
"""
import colorsys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

CLASSES = ["cotton", "silk", "wool", "linen", "polyester", "denim", "nylon", "rayon", "velvet", "blended"]


def _noise(rng, size, sigma):
    n = gaussian_filter(rng.normal(size=(size, size)), sigma)
    return (n / (n.std() + 1e-8)).astype(np.float32)


def _aniso(rng, size, sy, sx):
    n = gaussian_filter(rng.normal(size=(size, size)), (sy, sx))
    return (n / (n.std() + 1e-8)).astype(np.float32)


def _plain(x, y, p, rng):
    a, b = rng.uniform(0, 6.28, 2)
    return np.sin(2 * np.pi * x / p + a) * np.sin(2 * np.pi * y / p + b)


def _color(rng, h, s, v):
    hue = rng.uniform(*h) if isinstance(h, tuple) else h
    return np.array(colorsys.hsv_to_rgb(hue % 1.0, rng.uniform(*s), rng.uniform(*v)), dtype=np.float32)


def generate_image(fabric: str, rng: np.random.Generator, size: int = 160) -> Image.Image:
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    anyhue = (0.0, 1.0)
    m = np.zeros((size, size), np.float32)
    sheen = np.zeros((size, size), np.float32)
    amp = 0.12
    if fabric == "cotton":
        m = _plain(x, y, rng.uniform(6, 9), rng) + 0.5 * _noise(rng, size, 1.0)
        col, amp = _color(rng, anyhue, (0.1, 0.5), (0.6, 0.95)), 0.13
    elif fabric == "silk":
        th = rng.uniform(0, 3.14)
        L = rng.uniform(60, 120)
        sheen = np.cos(2 * np.pi * (x * np.cos(th) + y * np.sin(th)) / L + rng.uniform(0, 6.28))
        m = 0.3 * _plain(x, y, rng.uniform(3, 4), rng)
        col, amp = _color(rng, anyhue, (0.5, 0.9), (0.5, 0.85)), 0.06
        sheen *= 0.28
    elif fabric == "wool":
        m = 0.6 * _plain(x, y, rng.uniform(9, 13), rng) + 2.0 * _noise(rng, size, 1.2)
        col, amp = _color(rng, (0.0, 0.15), (0.1, 0.45), (0.3, 0.7)), 0.13
    elif fabric == "linen":
        m = 0.7 * _plain(x, y, rng.uniform(7, 10), rng) + 1.2 * (_aniso(rng, size, 0.5, 8) + _aniso(rng, size, 8, 0.5))
        col, amp = _color(rng, (0.07, 0.13), (0.1, 0.35), (0.65, 0.92)), 0.12
    elif fabric == "polyester":
        m = _plain(x, y, rng.uniform(3, 5), rng)
        sheen = 0.05 * np.cos(2 * np.pi * x / rng.uniform(80, 140))
        col, amp = _color(rng, anyhue, (0.3, 0.9), (0.4, 0.95)), 0.07
    elif fabric == "denim":
        p = rng.uniform(5, 7)
        m = np.tanh(2 * np.sin(2 * np.pi * (x + y) / p + rng.uniform(0, 6.28))) + 0.6 * _aniso(rng, size, 12, 0.6)
        col, amp = _color(rng, (0.58, 0.64), (0.5, 0.85), (0.3, 0.6)), 0.2
    elif fabric == "nylon":
        m = 0.2 * _plain(x, y, rng.uniform(2, 3), rng)
        L = rng.uniform(25, 50)
        sheen = 0.35 * np.cos(2 * np.pi * (x + 0.5 * y) / L + rng.uniform(0, 6.28)) ** 3
        col, amp = _color(rng, anyhue, (0.4, 0.95), (0.4, 0.9)), 0.05
    elif fabric == "rayon":
        xw = x + 12 * np.sin(2 * np.pi * y / rng.uniform(50, 90) + rng.uniform(0, 6.28))
        m = 0.5 * _plain(xw, y, rng.uniform(4, 6), rng) + 0.9 * np.sin(2 * np.pi * xw / rng.uniform(30, 60))
        col, amp = _color(rng, anyhue, (0.4, 0.9), (0.5, 0.9)), 0.12
    elif fabric == "velvet":
        m = 1.3 * _aniso(rng, size, 0.6, 5) + 1.0 * _noise(rng, size, 20)
        col, amp = _color(rng, anyhue, (0.5, 0.95), (0.15, 0.4)), 0.2
    else:  # blended
        m = 1.5 * _noise(rng, size, 2.5) + 0.7 * _plain(x, y, rng.uniform(5, 8), rng) + 0.3 * _noise(rng, size, 0.8)
        col, amp = _color(rng, anyhue, (0.05, 0.35), (0.45, 0.8)), 0.1
    # Within-class variation / class overlap so the task is not trivially separable
    amp *= rng.uniform(0.5, 1.4)
    sheen = sheen * rng.uniform(0.4, 1.4)
    if rng.random() < 0.3:  # colour unrelated to class
        col = _color(rng, anyhue, (0.05, 0.9), (0.25, 0.95))
    shade = 1 + rng.uniform(0.03, 0.15) * _noise(rng, size, 30)
    lum = (1 + amp * m + sheen) * shade * rng.uniform(0.8, 1.2)
    img = col[None, None, :] * lum[..., None] + rng.normal(0, rng.uniform(0.01, 0.07), (size, size, 3))
    blur = rng.uniform(0, 1.6) if rng.random() < 0.6 else 0
    if blur > 0:
        img = gaussian_filter(img, (blur, blur, 0))
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def generate_dataset(n_per_class: int, seed: int = 42, classes=None):
    rng = np.random.default_rng(seed)
    images, labels = [], []
    for c in classes or CLASSES:
        for _ in range(n_per_class):
            images.append(generate_image(c, rng))
            labels.append(c)
    return images, labels
