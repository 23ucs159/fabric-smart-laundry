"""Strict upload validation. Never trusts the client-supplied filename or content type."""
import io

from PIL import Image, UnidentifiedImageError

from app.core.config import settings

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
Image.MAX_IMAGE_PIXELS = 50_000_000  # decompression-bomb guard


class ImageValidationError(ValueError):
    pass


def validate_image_bytes(data: bytes, filename: str | None = None) -> Image.Image:
    if not data:
        raise ImageValidationError("The uploaded file is empty.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise ImageValidationError(f"Image is larger than {settings.max_upload_mb} MB.")
    if filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise ImageValidationError("Unsupported file type. Allowed: JPG, PNG, WEBP.")
    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        img.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise ImageValidationError("The file is not a valid or readable image.")
    if fmt not in ALLOWED_FORMATS:
        raise ImageValidationError("Unsupported image format. Allowed: JPG, PNG, WEBP.")
    w, h = img.size
    if min(w, h) < settings.min_image_px:
        raise ImageValidationError(f"Image is too small (minimum {settings.min_image_px}px per side).")
    if max(w, h) > settings.max_image_px:
        raise ImageValidationError(f"Image is too large (maximum {settings.max_image_px}px per side).")
    return img
