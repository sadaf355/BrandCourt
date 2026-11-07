"""Deterministic image checks and explicitly approximate visual heuristics."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path


def extract_c2pa_metadata(path: Path) -> dict:
    """Read embedded C2PA manifest data without fetching trust anchors or other network data."""
    try:
        import c2pa
    except ImportError:
        return {"status": "needs_human_review", "reason": "The c2pa-python SDK is not installed."}
    try:
        with c2pa.Reader(str(path)) as reader:
            manifest = json.loads(reader.detailed_json())
    except Exception as exc:
        if type(exc).__name__ in {"_C2paManifestNotFound", "C2paManifestNotFound"}:
            return {"status": "no_manifest"}
        return {
            "status": "needs_human_review",
            "reason": f"C2PA metadata could not be read ({type(exc).__name__}).",
        }
    if not isinstance(manifest, dict):
        return {
            "status": "needs_human_review",
            "reason": "C2PA reader returned an invalid manifest structure.",
        }
    return {"status": "extracted", "manifest": manifest}


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError("Expected #RGB or #RRGGBB")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _srgb_to_linear(value: float) -> float:
    value /= 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def contrast_ratio(first: str, second: str) -> float:
    def luminance(color: str) -> float:
        red, green, blue = (_srgb_to_linear(value) for value in hex_rgb(color))
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue

    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _rgb_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    red, green, blue = (_srgb_to_linear(value) for value in rgb)
    x = (red * 0.4124 + green * 0.3576 + blue * 0.1805) / 0.95047
    y = red * 0.2126 + green * 0.7152 + blue * 0.0722
    z = (red * 0.0193 + green * 0.1192 + blue * 0.9505) / 1.08883

    def transform(value: float) -> float:
        return value ** (1 / 3) if value > 0.008856 else 7.787 * value + 16 / 116

    fx, fy, fz = transform(x), transform(y), transform(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e_2000(hex1: str, hex2: str) -> float:
    l1, a1, b1 = _rgb_lab(hex_rgb(hex1))
    l2, a2, b2 = _rgb_lab(hex_rgb(hex2))
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    cbar = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt(cbar**7 / (cbar**7 + 25**7)))
    ap1, ap2 = (1 + g) * a1, (1 + g) * a2
    cp1, cp2 = math.hypot(ap1, b1), math.hypot(ap2, b2)

    def hue(a: float, b: float) -> float:
        angle = math.degrees(math.atan2(b, a))
        return angle + 360 if angle < 0 else angle

    hp1, hp2 = (hue(ap1, b1) if cp1 else 0), (hue(ap2, b2) if cp2 else 0)
    dl, dc = l2 - l1, cp2 - cp1
    if not cp1 * cp2:
        dh = 0
    elif abs(hp2 - hp1) <= 180:
        dh = hp2 - hp1
    elif hp2 - hp1 > 180:
        dh = hp2 - hp1 - 360
    else:
        dh = hp2 - hp1 + 360
    d_h = 2 * math.sqrt(cp1 * cp2) * math.sin(math.radians(dh / 2))
    lbar, cpbar = (l1 + l2) / 2, (cp1 + cp2) / 2
    if not cp1 * cp2:
        hpbar = hp1 + hp2
    elif abs(hp1 - hp2) <= 180:
        hpbar = (hp1 + hp2) / 2
    elif hp1 + hp2 < 360:
        hpbar = (hp1 + hp2 + 360) / 2
    else:
        hpbar = (hp1 + hp2 - 360) / 2
    t = (
        1
        - 0.17 * math.cos(math.radians(hpbar - 30))
        + 0.24 * math.cos(math.radians(2 * hpbar))
        + 0.32 * math.cos(math.radians(3 * hpbar + 6))
        - 0.20 * math.cos(math.radians(4 * hpbar - 63))
    )
    dtheta = 30 * math.exp(-((hpbar - 275) / 25) ** 2)
    rc = 2 * math.sqrt(cpbar**7 / (cpbar**7 + 25**7))
    sl = 1 + 0.015 * (lbar - 50) ** 2 / math.sqrt(20 + (lbar - 50) ** 2)
    sc, sh = 1 + 0.045 * cpbar, 1 + 0.015 * cpbar * t
    rt = -math.sin(math.radians(2 * dtheta)) * rc
    return math.sqrt((dl / sl) ** 2 + (dc / sc) ** 2 + (d_h / sh) ** 2 + rt * (dc / sc) * (d_h / sh))


def _hex_from_rgb(rgb) -> str:
    return "#%02X%02X%02X" % tuple(round(max(0, min(255, value))) for value in rgb)


def _kmeans_palette(image, palette: list[str], limit: float) -> tuple[list[dict], list[dict]]:
    import numpy as np
    from PIL import Image

    width, height = image.size
    sample = image.copy()
    sample.thumbnail((180, 180))
    pixels = np.asarray(sample, dtype=np.float32).reshape(-1, 3)
    unique_pixels = np.unique(pixels, axis=0)
    count = min(4, len(unique_pixels))
    centers = [unique_pixels[0]]
    for _ in range(1, count):
        distances = np.min(
            np.stack([np.sum((unique_pixels - center) ** 2, axis=1) for center in centers]),
            axis=0,
        )
        centers.append(unique_pixels[int(np.argmax(distances))])
    centers = np.asarray(centers, dtype=np.float32)
    labels = np.zeros(len(pixels), dtype=np.int32)
    for _ in range(8):
        distances = np.sum((pixels[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        labels = np.argmin(distances, axis=1)
        updated = np.array(
            [
                pixels[labels == index].mean(axis=0) if np.any(labels == index) else centers[index]
                for index in range(count)
            ],
            dtype=np.float32,
        )
        if np.allclose(updated, centers):
            break
        centers = updated

    sample_width, sample_height = sample.size
    label_image = labels.reshape(sample_height, sample_width)
    checks, findings = [], []
    for index in np.argsort(np.bincount(labels, minlength=count))[::-1]:
        rgb = centers[index]
        observed = _hex_from_rgb(rgb)
        nearest = min(palette, key=lambda value: delta_e_2000(observed, value))
        distance = delta_e_2000(observed, nearest)
        ys, xs = np.where(label_image == index)
        region = {
            "x": int(xs.min() * width / sample_width),
            "y": int(ys.min() * height / sample_height),
            "width": max(1, int((xs.max() + 1) * width / sample_width) - int(xs.min() * width / sample_width)),
            "height": max(1, int((ys.max() + 1) * height / sample_height) - int(ys.min() * height / sample_height)),
            "image_width": width,
            "image_height": height,
        }
        check = {
            "observed": observed,
            "nearest_brand_color": nearest,
            "delta_e_2000": round(distance, 2),
            "threshold": limit,
            "status": "pass" if distance <= limit else "review",
            "region": region,
            "method": "deterministic k-means cluster compared with palette using CIEDE2000",
        }
        checks.append(check)
        if distance > limit:
            findings.append(
                {
                    "code": "brand_color_mismatch",
                    "status": "needs_human_review",
                    "severity": "major",
                    "region": region,
                    "message": (
                        f"Deterministic palette check: dominant region {observed} is "
                        f"{distance:.1f} CIEDE2000 units from brand color {nearest} "
                        f"(configured limit {limit:g})."
                    ),
                    "analysis_method": "image_colour_ciede2000",
                }
            )
    return checks, findings


def _contrast_checks(image, boxes: list[dict]) -> tuple[dict, list[dict]]:
    import numpy as np

    width, height = image.size
    checks, findings = [], []
    for box in boxes:
        x, y = box["x"], box["y"]
        right, bottom = min(width, x + box["width"]), min(height, y + box["height"])
        if x < 0 or y < 0 or right <= x or bottom <= y:
            continue
        pad = max(2, min(8, int(min(box["width"], box["height"]) * 0.15)))
        outer_left, outer_top = max(0, x - pad), max(0, y - pad)
        outer_right, outer_bottom = min(width, right + pad), min(height, bottom + pad)
        background_samples = [
            image.crop((outer_left, outer_top, outer_right, y)),
            image.crop((outer_left, bottom, outer_right, outer_bottom)),
            image.crop((outer_left, y, x, bottom)),
            image.crop((right, y, outer_right, bottom)),
        ]
        background_pixels = [
            np.asarray(sample, dtype=np.uint8).reshape(-1, 3)
            for sample in background_samples
            if sample.width and sample.height
        ]
        if not background_pixels:
            continue
        bg = tuple(round(value) for value in np.median(np.concatenate(background_pixels), axis=0))
        text_pixels = np.asarray(image.crop((x, y, right, bottom)), dtype=np.uint8).reshape(-1, 3)
        if not len(text_pixels):
            continue
        luminance = text_pixels @ np.array([0.2126, 0.7152, 0.0722])
        ordered = text_pixels[np.argsort(luminance)]
        n = max(1, len(ordered) // 5)
        dark_color = tuple(round(value) for value in ordered[:n].mean(axis=0))
        light_color = tuple(round(value) for value in ordered[-n:].mean(axis=0))
        ratio = max(
            contrast_ratio(_hex_from_rgb(bg), _hex_from_rgb(dark_color)),
            contrast_ratio(_hex_from_rgb(bg), _hex_from_rgb(light_color)),
        )
        large_text = box["height"] >= 24
        threshold = 3.0 if large_text else 4.5
        check = {
            "text": box["text"],
            "ratio": round(ratio, 2),
            "threshold": threshold,
            "status": "pass" if ratio >= threshold else "review",
            "region": {
                "x": x, "y": y, "width": right - x, "height": bottom - y,
                "image_width": width, "image_height": height,
            },
            "method": "approximate sampled OCR-box foreground and surrounding-background colors",
        }
        checks.append(check)
        if ratio < threshold:
            findings.append(
                {
                    "code": "text_contrast",
                    "status": "needs_human_review",
                    "severity": "major",
                    "region": check["region"],
                    "message": (
                        f"Approximate contrast heuristic estimates {ratio:.2f}:1 "
                        f"(WCAG threshold {threshold:.1f}:1); confirm visually."
                    ),
                    "analysis_method": "image_contrast_heuristic",
                }
            )
    return {
        "status": "review" if findings else "pass" if checks else "needs_human_review",
        "minimum_estimated_ratio": min((item["ratio"] for item in checks), default=None),
        "checks": checks,
        "message": "Contrast is an approximate heuristic and requires visual confirmation.",
    }, findings


def _logo_match(image, logo_reference: Path | None) -> tuple[dict, list[dict]]:
    image_width, image_height = image.size
    full_region = {
        "x": 0, "y": 0, "width": image_width, "height": image_height,
        "image_width": image_width, "image_height": image_height,
    }
    if logo_reference is None or not logo_reference.exists():
        return (
            {"status": "needs_human_review", "message": "Upload a logo asset to check logo presence."},
            [
                {
                    "code": "logo_detection_unavailable",
                    "status": "needs_human_review",
                    "severity": "major",
                    "region": full_region,
                    "message": "Logo presence could not be checked because no uploaded logo reference is configured.",
                    "analysis_method": "logo_detection_unavailable",
                }
            ],
        )
    try:
        import cv2
        import numpy as np
    except ImportError:
        return (
            {"status": "needs_human_review", "message": "Logo matching dependencies are unavailable."},
            [
                {
                    "code": "logo_detection_unavailable",
                    "status": "needs_human_review",
                    "severity": "major",
                    "region": full_region,
                    "message": "Logo matching dependencies are unavailable; verify the logo manually.",
                    "analysis_method": "logo_detection_unavailable",
                }
            ],
        )

    template = cv2.imread(str(logo_reference), cv2.IMREAD_GRAYSCALE)
    source = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
    if template is None or min(template.shape) < 12:
        return (
            {"status": "needs_human_review", "message": "The uploaded logo is too small or invalid to match."},
            [
                {
                    "code": "logo_detection_unavailable",
                    "status": "needs_human_review",
                    "severity": "major",
                    "region": full_region,
                    "message": "The uploaded logo is too small or invalid to match reliably.",
                    "analysis_method": "logo_detection_unavailable",
                }
            ],
        )
    source_h, source_w = source.shape
    search_scale = min(1.0, 1600 / max(source_w, source_h))
    if search_scale < 1:
        search_w, search_h = round(source_w * search_scale), round(source_h * search_scale)
        search_image = cv2.resize(source, (search_w, search_h), interpolation=cv2.INTER_AREA)
        template_w, template_h = round(template.shape[1] * search_scale), round(template.shape[0] * search_scale)
        if min(template_w, template_h) < 12:
            return (
                {"status": "needs_human_review", "message": "The logo is too small to match at this creative resolution."},
                [{
                    "code": "logo_detection_unavailable",
                    "status": "needs_human_review",
                    "severity": "major",
                    "region": full_region,
                    "message": "Logo detection was unreliable after safe image scaling; verify manually.",
                    "analysis_method": "logo_detection_heuristic",
                }],
            )
        template = cv2.resize(template, (template_w, template_h), interpolation=cv2.INTER_AREA)
    else:
        search_image = source
    search_h, search_w = search_image.shape
    logo_h, logo_w = template.shape
    candidates = []
    for scale_x in (0.65, 0.8, 1.0, 1.2, 1.45):
        for scale_y in (0.65, 0.8, 1.0, 1.2, 1.45):
            new_w, new_h = round(logo_w * scale_x), round(logo_h * scale_y)
            if new_w < 12 or new_h < 12 or new_w > search_w or new_h > search_h:
                continue
            scaled = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)
            match = cv2.matchTemplate(search_image, scaled, cv2.TM_CCOEFF_NORMED)
            _minimum, maximum, _min_location, location = cv2.minMaxLoc(match)
            candidates.append((float(maximum), location, new_w, new_h))
    if not candidates or min(source_w, source_h) < 96:
        return (
            {"status": "needs_human_review", "message": "The creative is too small for reliable logo matching."},
            [
                {
                    "code": "logo_detection_unavailable",
                    "status": "needs_human_review",
                    "severity": "major",
                    "region": full_region,
                    "message": "Logo detection was unreliable at this image resolution; verify manually.",
                    "analysis_method": "logo_detection_heuristic",
                }
            ],
        )

    score, (x, y), width, height = max(candidates, key=lambda item: item[0])
    x, y = round(x / search_scale), round(y / search_scale)
    width, height = round(width / search_scale), round(height / search_scale)
    region = {
        "x": int(x), "y": int(y), "width": width, "height": height,
        "image_width": source_w, "image_height": source_h,
    }
    aspect_error = abs((width / height) / (logo_w / logo_h) - 1)
    if score >= 0.68 and aspect_error > 0.05:
        status = "distorted"
        message = "Approximate multi-scale template matching found a logo with an aspect ratio changed by more than 5%."
    elif score >= 0.68:
        status = "present"
        message = "Approximate multi-scale template matching found the uploaded logo reference."
    elif score < 0.35:
        status = "missing"
        message = "The reliable multi-scale template search found no matching uploaded logo reference."
    else:
        status = "needs_human_review"
        message = "Approximate logo matching was inconclusive; verify the logo manually."
    finding = []
    if status != "present":
        finding.append(
            {
                "code": f"logo_{status}",
                "status": "needs_human_review",
                "severity": "major",
                "region": region if status in {"distorted", "needs_human_review"} else full_region,
                "message": message,
                "analysis_method": "logo_detection_heuristic",
            }
        )
    return (
        {
            "status": status,
            "score": round(score, 3),
            "aspect_ratio_deviation": round(aspect_error, 4),
            "region": region if score >= 0.35 else full_region,
            "message": message,
        },
        finding,
    )


def analyze_image(
    path: Path,
    palette: list[str] | None = None,
    logo_reference: Path | None = None,
    *,
    delta_e_limit: float | None = None,
    c2pa_path: Path | None = None,
) -> dict:
    from PIL import Image, ImageFile, ImageOps
    from app.services.ocr import extract_text

    limit = delta_e_limit
    if limit is None:
        limit = float(os.environ.get("BRAND_COLOR_DELTA_E_LIMIT", "5"))
    if not math.isfinite(limit) or limit < 0:
        raise ValueError("BRAND_COLOR_DELTA_E_LIMIT must be a finite non-negative number.")
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    with Image.open(path) as source:
        source.load()
        image = ImageOps.exif_transpose(source).convert("RGB")
    width, height = image.size
    thumb = image.copy()
    thumb.thumbnail((180, 180))
    dominant = []
    for color in thumb.getcolors(maxcolors=32400) or []:
        dominant.append((color[0], _hex_from_rgb(color[1])))
    dominant = [color for _, color in sorted(dominant, reverse=True)[:8]]

    palette_checks, findings = [], []
    if palette:
        palette_checks, color_findings = _kmeans_palette(image, palette, limit)
        findings.extend(color_findings)

    ocr = extract_text(path)
    boxes = ocr["boxes"]
    contrast, contrast_findings = _contrast_checks(image, boxes)
    findings.extend(contrast_findings)
    for uncertain_word in ocr.get("uncertain_words", []):
        findings.append(
            {
                "code": "ocr_low_confidence",
                "status": "needs_human_review",
                "severity": "major",
                "region": {
                    **uncertain_word["region"],
                    "image_width": width,
                    "image_height": height,
                },
                "message": (
                    f"OCR word {uncertain_word['text']!r} is uncertain "
                    f"({uncertain_word['confidence']:.0%} confidence; "
                    f"threshold {uncertain_word['threshold']:.0%}). "
                    "Its line was withheld from Claim Court and requires human verification."
                ),
                "analysis_method": "ocr_confidence",
            }
        )
    logo_check, logo_findings = _logo_match(image, logo_reference)
    findings.extend(logo_findings)

    if ocr["status"] in {"unavailable", "failed"}:
        findings.append(
            {
                "code": "ocr_unavailable",
                "status": "needs_human_review",
                "severity": "major",
                "region": None,
                "message": ocr["message"],
                "analysis_method": "ocr_failure",
            }
        )
    elif ocr["status"] == "no_text_found":
        findings.append(
            {
                "code": "ocr_no_text",
                "status": "needs_human_review",
                "severity": "advisory",
                "region": {"x": 0, "y": 0, "width": width, "height": height, "image_width": width, "image_height": height},
                "message": "No text was detected in the creative; text checks continue using the caption.",
                "analysis_method": "ocr_no_text",
            }
        )

    c2pa = extract_c2pa_metadata(c2pa_path or path)
    if c2pa["status"] == "needs_human_review":
        findings.append(
            {
                "code": "c2pa_unavailable",
                "status": "needs_human_review",
                "severity": "advisory",
                "region": None,
                "message": c2pa.get("reason", "C2PA metadata could not be read."),
                "analysis_method": "c2pa_failure",
            }
        )
    return {
        "width": width,
        "height": height,
        "dominant_colors": dominant,
        "palette_checks": palette_checks,
        "ocr_status": ocr["status"],
        "ocr_message": ocr["message"],
        "ocr_boxes": boxes,
        "ocr_text": ocr["text"],
        "ocr_claim_text": ocr.get("claim_text", ocr["text"]),
        "ocr_confidence_threshold": ocr.get("confidence_threshold"),
        "ocr_uncertain_words": ocr.get("uncertain_words", []),
        "contrast": contrast,
        "logo_check": logo_check,
        "c2pa": c2pa,
        "findings": findings,
        "overall_status": "needs_human_review" if findings else "review",
        "failure_policy": "Every failed or inconclusive image check requires human review; no failure becomes an approval.",
    }
