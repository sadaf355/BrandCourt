"""Tesseract OCR adapter with explicit failure states and word-level boxes."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import math


def extract_text(path: Path, languages: tuple[str, ...] = ("eng", "hin", "mar")) -> dict:
    from app.core.config import settings

    confidence_threshold = settings.ocr_confidence_threshold
    try:
        import pytesseract

        executable = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
        if not executable:
            for candidate in (
                Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
                / "Tesseract-OCR"
                / "tesseract.exe",
                Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
                / "Tesseract-OCR"
                / "tesseract.exe",
            ):
                if candidate.is_file():
                    executable = str(candidate)
                    break
        if executable:
            pytesseract.pytesseract.tesseract_cmd = executable

        data = pytesseract.image_to_data(
            str(path),
            lang="+".join(languages),
            config="--psm 11",
            output_type=pytesseract.Output.DICT,
            timeout=30,
        )
    except ImportError:
        return {
            "status": "unavailable",
            "text": "",
            "boxes": [],
            "message": "OCR bindings are unavailable; image text needs human review.",
        }
    except Exception as exc:
        try:
            import pytesseract

            unavailable = isinstance(exc, pytesseract.TesseractNotFoundError)
        except ImportError:
            unavailable = False
        return {
            "status": "unavailable" if unavailable else "failed",
            "text": "",
            "boxes": [],
            "message": (
                "Tesseract is unavailable; image text needs human review."
                if unavailable
                else f"OCR failed ({type(exc).__name__}); image text needs human review."
            ),
        }

    boxes = []
    for index, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text).strip()
        if not text:
            continue
        try:
            confidence = float(data["conf"][index])
        except (IndexError, TypeError, ValueError):
            confidence = 0.0
        if not math.isfinite(confidence) or confidence < 0:
            confidence = 0.0
        boxes.append(
            {
                "text": text,
                "confidence": round(confidence / 100, 3),
                "x": int(data["left"][index]),
                "y": int(data["top"][index]),
                "width": int(data["width"][index]),
                "height": int(data["height"][index]),
                "block_num": int(data.get("block_num", [0] * len(data["text"]))[index] or 0),
                "par_num": int(data.get("par_num", [0] * len(data["text"]))[index] or 0),
                "line_num": int(data.get("line_num", [0] * len(data["text"]))[index] or 0),
                "uncertain": confidence / 100 < confidence_threshold,
            }
        )

    text = " ".join(box["text"] for box in boxes)
    if not text:
        return {
            "status": "no_text_found",
            "text": "",
            "claim_text": "",
            "boxes": [],
            "uncertain_words": [],
            "confidence_threshold": confidence_threshold,
            "message": "No usable text was detected in the creative.",
        }
    line_words: dict[tuple[int, int, int], list[dict]] = {}
    for box in boxes:
        line_key = (box["block_num"], box["par_num"], box["line_num"])
        line_words.setdefault(line_key, []).append(box)
    claim_lines = [
        " ".join(box["text"] for box in line)
        for line in line_words.values()
        if all(not box["uncertain"] for box in line)
    ]
    uncertain_words = [
        {
            "text": box["text"],
            "confidence": box["confidence"],
            "threshold": confidence_threshold,
            "region": {
                "x": box["x"],
                "y": box["y"],
                "width": box["width"],
                "height": box["height"],
            },
        }
        for box in boxes
        if box["uncertain"]
    ]
    return {
        "status": "completed",
        "text": text,
        "claim_text": "\n".join(claim_lines),
        "boxes": boxes,
        "uncertain_words": uncertain_words,
        "confidence_threshold": confidence_threshold,
        "message": (
            f"OCR completed using Tesseract (English, Hindi and Marathi); "
            f"{len(uncertain_words)} word(s) are below the "
            f"{confidence_threshold:.0%} confidence threshold and need human review."
            if uncertain_words
            else "OCR completed using Tesseract (English, Hindi and Marathi)."
        ),
    }
