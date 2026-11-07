import asyncio
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select

from app.services.image_intelligence import (
    analyze_image,
    contrast_ratio,
    delta_e_2000,
    extract_c2pa_metadata,
)
from app.services.ocr import extract_text
from app.models.entities import ContentRevision, ReviewJob


def _configure_real_tesseract():
    import pytesseract

    executable = shutil.which("tesseract") or shutil.which("tesseract.exe")
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
    if not executable:
        pytest.skip("Real OCR integration requires an installed Tesseract executable.")

    languages = subprocess.run(
        [executable, "--list-langs"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout
    missing = [language for language in ("eng", "hin", "mar") if language not in languages.split()]
    if missing:
        pytest.skip(f"Real OCR integration requires Tesseract language data: {', '.join(missing)}.")
    pytesseract.pytesseract.tesseract_cmd = executable


def _ocr_fixture_font(size: int):
    candidates = [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "Nirmala.ttc",
        Path("DejaVuSans.ttf"),
        Path("arial.ttf"),
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    pytest.skip("No suitable TrueType font is available for real OCR fixtures.")


def test_contrast_ratio_known_values():
    assert round(contrast_ratio('#000000','#FFFFFF'),2)==21.0

def test_ciede2000_same_color_and_distance():
    assert delta_e_2000('#FFFFFF','#FFFFFF') < 0.01
    assert delta_e_2000('#FFFFFF','#000000') > 50


def test_ocr_no_text_is_an_explicit_human_review(monkeypatch, tmp_path):
    image_path = tmp_path / "blank.png"
    Image.new("RGB", (40, 40), "white").save(image_path)
    monkeypatch.setattr(
        "app.services.ocr.extract_text",
        lambda *_args, **_kwargs: {
            "status": "no_text_found",
            "text": "",
            "boxes": [],
            "message": "No usable text was detected in the creative.",
        },
    )

    result = analyze_image(image_path, palette=["#FFFFFF"])

    assert result["ocr_text"] == ""
    assert result["ocr_boxes"] == []
    assert result["overall_status"] == "needs_human_review"
    assert result["c2pa"]["status"] == "no_manifest"
    assert "no failure becomes an approval" in result["failure_policy"]


def test_ocr_engine_failure_is_not_converted_to_no_text(monkeypatch, tmp_path):
    image_path = tmp_path / "blank.png"
    Image.new("RGB", (40, 40), "white").save(image_path)

    monkeypatch.setattr(
        "app.services.ocr.extract_text",
        lambda *_args, **_kwargs: {
            "status": "unavailable",
            "text": "",
            "boxes": [],
            "message": "Tesseract is unavailable; image text needs human review.",
        },
    )
    result = analyze_image(image_path, palette=["#FFFFFF"])

    assert result["ocr_status"] == "unavailable"
    assert any(item["code"] == "ocr_unavailable" for item in result["findings"])


def test_tesseract_adapter_returns_word_boxes_for_all_requested_languages(monkeypatch, tmp_path):
    import pytesseract

    image_path = tmp_path / "creative.png"
    Image.new("RGB", (40, 30), "white").save(image_path)
    observed = {}

    def fake_ocr(_path, **kwargs):
        observed.update(kwargs)
        return {
            "text": ["Namaste", ""],
            "conf": ["92", "-1"],
            "left": ["2", "0"],
            "top": ["4", "0"],
            "width": ["20", "0"],
            "height": ["8", "0"],
        }

    monkeypatch.setattr(pytesseract, "image_to_data", fake_ocr)
    result = extract_text(image_path)

    assert observed["lang"] == "eng+hin+mar"
    assert result["status"] == "completed"
    assert result["text"] == "Namaste"
    assert result["boxes"] == [{
        "text": "Namaste", "confidence": 0.92,
        "x": 2, "y": 4, "width": 20, "height": 8,
        "block_num": 0, "par_num": 0, "line_num": 0, "uncertain": False,
    }]


@pytest.mark.parametrize(
    ("language", "uncertain_word"),
    [
        ("hin", "\u0909\u0924\u094d\u092a\u093e\u0926"),
        ("mar", "\u0909\u0924\u094d\u092a\u093e\u0926\u0928"),
    ],
)
def test_low_confidence_hindi_and_marathi_text_is_preserved_but_withheld(
    language, uncertain_word, monkeypatch, tmp_path
):
    import pytesseract
    from app.core.config import settings

    image_path = tmp_path / f"low-confidence-{language}.png"
    Image.new("RGB", (300, 80), "white").save(image_path)
    monkeypatch.setattr(settings, "ocr_confidence_threshold", 0.7)
    monkeypatch.setattr(
        pytesseract,
        "image_to_data",
        lambda *_args, **_kwargs: {
            "text": [uncertain_word, "50"],
            "conf": ["33", "95"],
            "left": ["12", "145"],
            "top": ["20", "20"],
            "width": ["100", "40"],
            "height": ["30", "28"],
            "block_num": ["1", "1"],
            "par_num": ["1", "1"],
            "line_num": ["1", "1"],
        },
    )

    result = extract_text(image_path, languages=(language,))

    assert result["text"] == f"{uncertain_word} 50"
    assert result["claim_text"] == ""
    assert result["confidence_threshold"] == 0.7
    assert result["boxes"][0]["text"] == uncertain_word
    assert result["boxes"][0]["confidence"] == 0.33
    assert result["boxes"][0]["uncertain"] is True
    assert result["boxes"][1]["text"] == "50"
    assert result["boxes"][1]["confidence"] == 0.95
    assert result["boxes"][1]["uncertain"] is False
    assert result["uncertain_words"] == [{
        "text": uncertain_word,
        "confidence": 0.33,
        "threshold": 0.7,
        "region": {"x": 12, "y": 20, "width": 100, "height": 30},
    }]
    assert "1 word(s)" in result["message"]


def test_high_confidence_english_text_remains_claimcourt_eligible(
    monkeypatch, tmp_path
):
    import pytesseract
    from app.core.config import settings

    image_path = tmp_path / "high-confidence-english.png"
    Image.new("RGB", (320, 80), "white").save(image_path)
    monkeypatch.setattr(settings, "ocr_confidence_threshold", 0.7)
    monkeypatch.setattr(
        pytesseract,
        "image_to_data",
        lambda *_args, **_kwargs: {
            "text": ["Save", "50", "percent", "today."],
            "conf": ["96", "95", "94", "96"],
            "left": ["10", "90", "140", "240"],
            "top": ["20", "20", "20", "20"],
            "width": ["65", "35", "85", "65"],
            "height": ["30", "30", "30", "30"],
            "block_num": ["1", "1", "1", "1"],
            "par_num": ["1", "1", "1", "1"],
            "line_num": ["1", "1", "1", "1"],
        },
    )

    result = extract_text(image_path, languages=("eng",))

    assert result["text"] == "Save 50 percent today."
    assert result["claim_text"] == result["text"]
    assert not result["uncertain_words"]
    assert all(not box["uncertain"] for box in result["boxes"])


def test_tesseract_executable_failure_is_visible(monkeypatch, tmp_path):
    import pytesseract

    def missing_engine(*_args, **_kwargs):
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(pytesseract, "image_to_data", missing_engine)
    result = extract_text(tmp_path / "creative.png")

    assert result["status"] == "unavailable"
    assert not result["text"]
    assert "human review" in result["message"]


@pytest.mark.parametrize(
    ("language", "fixture_text", "expected_token"),
    [
        ("eng", "Save 50 percent today.", "50"),
        (
            "hin",
            "\u0906\u091c \u0928\u092f\u093e \u0909\u0924\u094d\u092a\u093e\u0926 "
            "\u0916\u0930\u0940\u0926\u0947\u0902\u0964",
            "\u0909\u0924\u094d\u092a\u093e\u0926",
        ),
        (
            "mar",
            "\u0906\u091c \u0928\u0935\u0940\u0928 \u0909\u0924\u094d\u092a\u093e\u0926\u0928 "
            "\u0916\u0930\u0947\u0926\u0940 \u0915\u0930\u093e\u0964",
            "\u0906\u091c",
        ),
    ],
)
def test_real_tesseract_recognizes_multilingual_text_and_word_boxes(
    language, fixture_text, expected_token, tmp_path
):
    _configure_real_tesseract()
    image = Image.new("RGB", (1800, 200), "white")
    ImageDraw.Draw(image).text(
        (40, 30),
        fixture_text,
        font=_ocr_fixture_font(72),
        fill="black",
    )
    image_path = tmp_path / f"real-ocr-{language}.png"
    image.save(image_path)

    result = extract_text(image_path, languages=(language,))

    assert result["status"] == "completed", result["message"]
    normalized_text = result["text"].replace("\u200c", "").replace("\u200d", "")
    assert expected_token in normalized_text
    assert result["boxes"]
    matching_boxes = [
        box for box in result["boxes"]
        if expected_token in box["text"].replace("\u200c", "").replace("\u200d", "")
    ]
    assert matching_boxes
    assert all(
        box["x"] >= 0
        and box["y"] >= 0
        and box["width"] > 0
        and box["height"] > 0
        and box["x"] + box["width"] <= image.width
        and box["y"] + box["height"] <= image.height
        for box in result["boxes"]
    )
    assert all(box["confidence"] > 0 for box in matching_boxes)


def test_real_tesseract_blank_image_is_explicit_no_text(tmp_path):
    _configure_real_tesseract()
    image_path = tmp_path / "real-ocr-blank.png"
    Image.new("RGB", (800, 200), "white").save(image_path)

    result = extract_text(image_path)

    assert result["status"] == "no_text_found"
    assert result["text"] == ""
    assert result["boxes"] == []


def test_off_brand_kmeans_result_has_a_highlight_region(monkeypatch, tmp_path):
    image_path = tmp_path / "off-brand.png"
    Image.new("RGB", (120, 80), "#F00020").save(image_path)
    monkeypatch.setattr(
        "app.services.ocr.extract_text",
        lambda *_args, **_kwargs: {
            "status": "no_text_found", "text": "", "boxes": [], "message": "No text."
        },
    )

    result = analyze_image(image_path, palette=["#0000FF"])

    finding = next(item for item in result["findings"] if item["code"] == "brand_color_mismatch")
    assert finding["status"] == "needs_human_review"
    assert finding["region"]["width"] == 120
    assert finding["region"]["height"] == 80
    assert "CIEDE2000" in finding["message"]


def test_low_contrast_ocr_box_uses_wcag_large_text_threshold(monkeypatch, tmp_path):
    image_path = tmp_path / "low-contrast.png"
    image = Image.new("RGB", (100, 60), "#777777")
    image.save(image_path)
    monkeypatch.setattr(
        "app.services.ocr.extract_text",
        lambda *_args, **_kwargs: {
            "status": "completed",
            "text": "Brand",
            "boxes": [{"text": "Brand", "confidence": 0.9, "x": 20, "y": 15, "width": 60, "height": 30}],
            "message": "OCR completed.",
        },
    )

    result = analyze_image(image_path, palette=["#777777"])
    finding = next(item for item in result["findings"] if item["code"] == "text_contrast")

    assert finding["region"]["x"] == 20
    assert "3.0:1" in finding["message"]
    assert finding["analysis_method"] == "image_contrast_heuristic"


def test_logo_template_matching_detects_present_missing_and_distorted(tmp_path):
    import numpy as np
    from app.services.image_intelligence import _logo_match

    template = Image.new("RGB", (48, 28), "white")
    for x in range(5, 40):
        for y in range(5, 23):
            template.putpixel((x, y), (15, 55, 180) if (x + y) % 3 else (240, 160, 10))
    template_path = tmp_path / "logo.png"
    template.save(template_path)

    present = Image.new("RGB", (220, 140), "white")
    present.paste(template, (80, 55))
    status, findings = _logo_match(present, template_path)
    assert status["status"] == "present"
    assert findings == []
    assert status["region"]["width"] == 48

    distorted = Image.new("RGB", (220, 140), "white")
    distorted.paste(template.resize((60, 28)), (80, 55))
    distorted_status, distorted_findings = _logo_match(distorted, template_path)
    assert distorted_status["status"] == "distorted"
    assert distorted_findings[0]["region"]

    missing = Image.fromarray(np.random.default_rng(42).integers(0, 256, (140, 220, 3), dtype=np.uint8))
    missing_status, missing_findings = _logo_match(missing, template_path)
    assert missing_status["status"] == "missing"
    assert missing_status["region"] == {
        "x": 0, "y": 0, "width": 220, "height": 140,
        "image_width": 220, "image_height": 140,
    }
    assert missing_findings[0]["region"]


def test_creative_upload_runs_visual_and_ocr_claim_checks_in_same_job(
    api_client, workspace_users, auth_headers, test_database, tmp_path, monkeypatch
):
    import io
    from app.core.storage import LocalStorage
    from app.core.job_worker import process_next_job
    from app.models.entities import ClaimFinding
    from PIL import Image

    _users, content_id, workspace_ids = workspace_users
    storage = LocalStorage(tmp_path)
    monkeypatch.setattr("app.api.content.get_storage", lambda: storage)
    monkeypatch.setattr(
        "app.services.ocr.extract_text",
        lambda *_args, **_kwargs: {
            "status": "completed",
            "text": "Save 50% today.",
            "boxes": [{
                "text": "Save 50% today.", "confidence": 0.99,
                "x": 20, "y": 20, "width": 90, "height": 20,
            }],
            "message": "OCR completed using Tesseract (English, Hindi and Marathi).",
        },
    )
    palette = api_client(
        "POST",
        "/api/assets",
        headers=auth_headers(1, "admin"),
        json={"kind": "palette", "name": "Brand palette", "data": {"colors": ["#0000FF"]}},
    )
    assert palette.status_code == 201
    image = Image.new("RGB", (140, 80), "#F00020")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    uploaded = api_client(
        "POST",
        f"/api/content/{content_id}/creative",
        headers=auth_headers(1, "creator"),
        files={"file": ("creative.png", image_bytes.getvalue(), "image/png")},
    )
    assert uploaded.status_code == 201
    queued = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        headers=auth_headers(1, "creator"),
    )
    assert queued.status_code == 202
    job_id = queued.json()["job_id"]
    assert asyncio.run(process_next_job(test_database, worker_id="visual-integration"))

    async def get_job_and_findings():
        async with test_database() as session:
            job = await session.get(ReviewJob, job_id)
            findings = (
                await session.scalars(
                    select(ClaimFinding).where(
                        ClaimFinding.workspace_id == workspace_ids[1],
                        ClaimFinding.revision_id == job.revision_id,
                    )
                )
            ).all()
            revision = await session.get(ContentRevision, job.revision_id)
            return job, findings, revision

    job, findings, revision = asyncio.run(get_job_and_findings())
    assert job.status == "completed", job.error
    assert revision.ocr_status == "completed"
    assert revision.ocr_text == "Save 50% today."
    assert revision.image_analysis["upload"]["thumbnail_storage_key"]
    visual = [finding for finding in findings if finding.layer == "visual"]
    assert any(finding.region and finding.analysis_method == "image_colour_ciede2000" for finding in visual)
    assert any(finding.layer == "claims" and "50%" in finding.claim_text for finding in findings)
    assert any(item["layer"] == "visual" and item["region"] for item in job.result["findings"])


def test_real_ocr_reaches_claim_court_in_durable_api_worker_job(
    api_client, workspace_users, auth_headers, test_database, tmp_path, monkeypatch
):
    import io
    from app.core.job_worker import process_next_job
    from app.core.storage import LocalStorage
    from app.models.entities import ClaimFinding

    _configure_real_tesseract()
    _users, content_id, workspace_ids = workspace_users
    storage = LocalStorage(tmp_path)
    monkeypatch.setattr("app.api.content.get_storage", lambda: storage)
    image = Image.new("RGB", (1800, 200), "white")
    ImageDraw.Draw(image).text(
        (40, 30),
        "Save 50 percent today.",
        font=ImageFont.truetype(
            str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arialbd.ttf"),
            72,
        ),
        fill="black",
    )
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")

    upload = api_client(
        "POST",
        f"/api/content/{content_id}/creative",
        headers=auth_headers(1, "creator"),
        files={"file": ("real-ocr.png", image_bytes.getvalue(), "image/png")},
    )
    assert upload.status_code == 201
    response = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        headers=auth_headers(1, "creator"),
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert asyncio.run(process_next_job(test_database, worker_id="real-ocr-worker"))

    async def load_job_state():
        async with test_database() as session:
            job = await session.get(ReviewJob, job_id)
            revision = await session.get(ContentRevision, job.revision_id)
            findings = (
                await session.scalars(
                    select(ClaimFinding).where(
                        ClaimFinding.workspace_id == workspace_ids[1],
                        ClaimFinding.revision_id == revision.id,
                    )
                )
            ).all()
            return job, revision, findings

    job, revision, findings = asyncio.run(load_job_state())
    assert job.status == "completed", job.error
    assert revision.ocr_status == "completed"
    assert "Save 50 percent today." in revision.ocr_text
    assert revision.image_analysis["ocr_boxes"]
    assert all(
        box["x"] + box["width"] <= revision.image_analysis["width"]
        and box["y"] + box["height"] <= revision.image_analysis["height"]
        for box in revision.image_analysis["ocr_boxes"]
    )
    claim_finding = next(
        (
            finding for finding in findings
            if "claims" in finding.layer.split(",") and "50 percent" in finding.claim_text.lower()
        ),
        None,
    )
    assert claim_finding is not None, [
        (finding.layer, finding.claim_text, finding.verdict) for finding in findings
    ]
    visual_finding = next(finding for finding in findings if finding.layer == "visual")
    assert claim_finding.verdict in {"unsupported", "needs_human_review", "supported"}
    assert visual_finding.region
    assert any(
        item["id"] == claim_finding.id and "claims" in item["layer"].split(",")
        for item in job.result["findings"]
    )
    assert any(
        item["id"] == visual_finding.id and item["layer"] == "visual" and item["region"]
        for item in job.result["findings"]
    )


def test_worker_withholds_low_confidence_ocr_and_creates_region_review_finding(
    api_client, workspace_users, auth_headers, test_database, tmp_path, monkeypatch
):
    import io
    import pytesseract
    from app.core.config import settings
    from app.core.job_worker import process_next_job
    from app.core.storage import LocalStorage
    from app.models.entities import ClaimFinding

    _users, content_id, workspace_ids = workspace_users
    monkeypatch.setattr(settings, "ocr_confidence_threshold", 0.7)
    monkeypatch.setattr(
        pytesseract,
        "image_to_data",
        lambda *_args, **_kwargs: {
            "text": ["\u0909\u0924\u094d\u092a\u093e\u0926", "50"],
            "conf": ["33", "95"],
            "left": ["12", "145"],
            "top": ["20", "20"],
            "width": ["100", "40"],
            "height": ["30", "28"],
            "block_num": ["1", "1"],
            "par_num": ["1", "1"],
            "line_num": ["1", "1"],
        },
    )
    storage = LocalStorage(tmp_path)
    monkeypatch.setattr("app.api.content.get_storage", lambda: storage)
    image = Image.new("RGB", (300, 80), "white")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")

    upload = api_client(
        "POST",
        f"/api/content/{content_id}/creative",
        headers=auth_headers(1, "creator"),
        files={"file": ("low-confidence.png", image_bytes.getvalue(), "image/png")},
    )
    assert upload.status_code == 201
    response = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        headers=auth_headers(1, "creator"),
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert asyncio.run(process_next_job(test_database, worker_id="low-confidence-ocr-worker"))

    async def load_state():
        async with test_database() as session:
            job = await session.get(ReviewJob, job_id)
            revision = await session.get(ContentRevision, job.revision_id)
            findings = (
                await session.scalars(
                    select(ClaimFinding).where(
                        ClaimFinding.workspace_id == workspace_ids[1],
                        ClaimFinding.revision_id == revision.id,
                    )
                )
            ).all()
            return job, revision, findings

    job, revision, findings = asyncio.run(load_state())
    assert job.status == "completed", job.error
    assert revision.ocr_text == "\u0909\u0924\u094d\u092a\u093e\u0926 50"
    assert revision.image_analysis["ocr_boxes"][0]["confidence"] == 0.33
    assert revision.image_analysis["ocr_boxes"][0]["uncertain"] is True
    assert revision.image_analysis["ocr_claim_text"] == ""
    uncertain = next(
        finding
        for finding in findings
        if finding.layer == "ocr" and finding.analysis_method == "ocr_confidence"
    )
    assert uncertain.verdict == "needs_human_review"
    assert uncertain.severity == "major"
    assert uncertain.region == {
        "x": 12, "y": 20, "width": 100, "height": 30,
        "image_width": 300, "image_height": 80,
    }
    assert "\u0909\u0924\u094d\u092a\u093e\u0926" in uncertain.claim_text
    assert not any(
        "claims" in finding.layer.split(",") and "50" in finding.claim_text
        for finding in findings
    )
    assert any(
        item["id"] == uncertain.id and item["verdict"] == "needs_human_review"
        for item in job.result["findings"]
    )


def test_c2pa_reader_returns_extracted_manifest(monkeypatch, tmp_path):
    import c2pa

    class Reader:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def detailed_json(self):
            return '{"active_manifest": "test-manifest", "manifests": {}}'

    monkeypatch.setattr(c2pa, "Reader", Reader)
    result = extract_c2pa_metadata(tmp_path / "with-manifest.jpg")

    assert result == {
        "status": "extracted",
        "manifest": {"active_manifest": "test-manifest", "manifests": {}},
    }


def test_c2pa_sdk_reports_manifest_absence_without_failing(tmp_path):
    image_path = tmp_path / "no-c2pa-manifest.png"
    Image.new("RGB", (8, 8), "white").save(image_path)
    assert extract_c2pa_metadata(image_path) == {"status": "no_manifest"}


@pytest.mark.parametrize(
    ("ocr_status", "expected_evidence_status"),
    [
        ("no_text_found", "no_text_found"),
        ("failed", "failed"),
    ],
)
def test_worker_surfaces_ocr_failure_and_no_text(
    ocr_status,
    expected_evidence_status,
    api_client,
    workspace_users,
    auth_headers,
    test_database,
    tmp_path,
    monkeypatch,
):
    from app.core.job_worker import process_next_job
    from app.core.storage import LocalStorage
    import io

    _users, content_id, workspace_ids = workspace_users
    storage = LocalStorage(tmp_path)
    image_key = f"{workspace_ids[1]}/creatives/creative.webp"
    image_bytes = io.BytesIO()
    Image.new("RGB", (120, 80), "white").save(image_bytes, format="WEBP")
    storage.put_bytes(image_key, image_bytes.getvalue(), "image/webp")
    monkeypatch.setattr("app.api.content.get_storage", lambda: storage)
    monkeypatch.setattr(
        "app.services.ocr.extract_text",
        lambda *_args, **_kwargs: {
            "status": ocr_status,
            "text": "",
            "boxes": [],
            "message": f"OCR {ocr_status}.",
        },
    )

    async def prepare():
        async with test_database() as session:
            revision = await session.scalar(
                select(ContentRevision).where(
                    ContentRevision.content_id == content_id,
                    ContentRevision.workspace_id == workspace_ids[1],
                )
            )
            revision.creative_storage_key = image_key
            revision.ocr_status = ocr_status
            await session.commit()

    asyncio.run(prepare())
    response = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        headers=auth_headers(1, "creator"),
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert asyncio.run(
        process_next_job(test_database, worker_id=f"ocr-{ocr_status}")
    )

    async def load_job():
        async with test_database() as session:
            return await session.get(ReviewJob, job_id)

    job = asyncio.run(load_job())
    assert job.status == "completed", job.error
    ocr_findings = [
        finding
        for finding in job.result["findings"]
        if finding.get("analysis_method") == "ocr_failure"
    ]
    assert len(ocr_findings) == 1
    assert ocr_findings[0]["verdict"] == "needs_human_review"
    assert ocr_findings[0]["evidence"][0]["status"] == expected_evidence_status
