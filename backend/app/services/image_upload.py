"""Content-based raster image validation, re-encoding, and thumbnail generation."""
from __future__ import annotations

import io

from PIL import Image, ImageOps


EXPECTED_FORMATS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
    ".gif": "GIF",
}


def reencode_image(raw: bytes, suffix: str) -> tuple[bytes, bytes, int, int]:
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.format != EXPECTED_FORMATS.get(suffix.lower()):
                raise ValueError("Uploaded file content does not match its image extension.")
            if source.width * source.height > 40_000_000:
                raise OverflowError("Image dimensions exceed the 40 megapixel safety limit.")
            source.seek(0)
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
            width, height = image.size
            processed = io.BytesIO()
            image.save(processed, format="WEBP", quality=92, method=6)
            thumbnail = image.copy()
            thumbnail.thumbnail((512, 512))
            thumb_bytes = io.BytesIO()
            thumbnail.save(thumb_bytes, format="WEBP", quality=82, method=6)
            return processed.getvalue(), thumb_bytes.getvalue(), width, height
    except (ValueError, OverflowError):
        raise
    except Exception as exc:
        raise ValueError("Uploaded file is not a valid supported image.") from exc
