"""Shared demo workspace provisioning and lifecycle management.
Idempotent staging for one-click demo login and CLI --demo seeding.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from fastapi import BackgroundTasks

from app.core.config import settings
from app.core.security import hash_password
from app.core.storage import get_storage, Storage
from app.db.session import SessionLocal
from app.models.entities import (
    User,
    Workspace,
    Rule,
    RuleExample,
    Fact,
    BrandAsset,
    ContentItem,
    ContentRevision,
    ClaimFinding,
    FindingDecision,
    Precedent,
    ReviewJob,
)
from app.core.job_queue import enqueue_review_job
from app.core.job_worker import process_next_job
from app.api.workflow import change_workflow, decide_finding, StateInput, DecisionInput
from app.api.intelligence import create_precedent, approve_precedent, PrecedentInput

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "sample" / "glowserum_40_posts.jsonl"
PAID_GIFTED_DECLARATION_POST_IDS = {"GC-021", "GC-022", "GC-023", "GC-024", "GC-025"}

RULES = [
    ("IN-1", "Substantiation for factual claims", "Factual, measurable, comparative or performance claims must have a traceable approved source. If no source is found, request human review; do not infer that the claim is false.", "required_text", "advisory"),
    ("IN-2", "Superlatives require proof", "Claims using best, only, #1, number one or equivalent superlatives require specific, current evidence.", "pattern", "critical"),
    ("IN-3", "Disclaimer cannot cure misleading main claim", "A disclaimer must not contradict or attempt to cure a misleading main claim. Flag absolute promises alongside disclaimer language for human review.", "disclosure", "critical"),
    ("IN-4", "Paid or gifted disclosure", "Paid or gifted creator content must use a clear disclosure such as #ad or Paid partnership, subject to current platform guidance.", "disclosure", "major"),
    ("IN-5", "Restricted cure and guaranteed-result wording", "Cure or guaranteed-result wording for health and skin products must be routed for human/legal review. This is not a legal determination.", "term", "critical"),
    ("IN-6", "AI-generated media declaration", "Realistic AI-generated image/video must include an AI disclosure label where required by current platform policy. This is an advisory reminder; check current platform policy.", "disclosure", "advisory"),
]

RULE_EXAMPLES: dict[str, tuple[str, str]] = {
    "IN-1": (
        "Helps hydrate dry skin for 4 weeks (based on approved study FACT-RESULTS).",
        "Clinically proven to boost skin hydration by 200% overnight.",
    ),
    "IN-2": (
        "Formulated for daily skin hydration with hyaluronic acid.",
        "India's #1 best skincare serum on the market.",
    ),
    "IN-3": (
        "Supports smoother-looking skin with daily use.",
        "Reverses ageing in 7 days! *Individual results may vary.",
    ),
    "IN-4": (
        "GlowSerum partner update: loving this hydrating routine! #ad",
        "Check out this gifted GlowSerum bottle I received from the brand!",
    ),
    "IN-5": (
        "May help improve the appearance of blemish-prone skin.",
        "Cures acne permanently with guaranteed results in 3 days.",
    ),
    "IN-6": (
        "AI-assisted studio background disclosed in caption and platform settings.",
        "Photorealistic AI-generated skin close-up posted without an AI label.",
    ),
    "DEMO-CONFLICT-A": (
        "Discover gentle daily hydration with GlowSerum.",
        "Discover gentle daily hydration with GlowSerum!",
    ),
    "DEMO-CONFLICT-B": (
        "Discover gentle daily hydration with GlowSerum!",
        "Discover gentle daily hydration with GlowSerum.",
    ),
    "DEMO-CONFLICT-C": (
        "GlowSerum 30 ml — ₹799 for daily hydration.",
        "GlowSerum 30 ml for daily hydration.",
    ),
    "DEMO-CONFLICT-D": (
        "GlowSerum 30 ml for daily hydration.",
        "GlowSerum 30 ml — ₹799 for daily hydration.",
    ),
    "DEMO-CONFLICT-E": (
        "30 ml daily hydrating serum. Apply morning and night.",
        "30 ml सीरम — सुबह और रात लगाएं।",
    ),
    "DEMO-CONFLICT-F": (
        "30 ml hydrating serum / 30 ml हाइड्रेटिंग सीरम।",
        "30 ml hydrating serum (English only).",
    ),
    "DEMO-CONFLICT-G": (
        "Hydrate your skin daily. Shop GlowSerum via the link in bio.",
        "Hydrate your skin daily with GlowSerum.",
    ),
    "DEMO-CONFLICT-H": (
        "Hydrate your skin daily with GlowSerum.",
        "Hydrate your skin daily. Shop GlowSerum via the link in bio.",
    ),
}


async def ensure_rule_examples(db: Any, rule: Rule) -> None:
    """Attach idempotent good/bad examples for a rule when defined in RULE_EXAMPLES."""
    pair = RULE_EXAMPLES.get(rule.code)
    if not pair:
        return
    good_text, bad_text = pair
    existing_kinds = set(
        (await db.scalars(select(RuleExample.kind).where(RuleExample.rule_id == rule.id))).all()
    )
    if "good" not in existing_kinds:
        db.add(RuleExample(rule_id=rule.id, kind="good", text=good_text))
    if "bad" not in existing_kinds:
        db.add(RuleExample(rule_id=rule.id, kind="bad", text=bad_text))

DEMO_DRAFTS = [
    {
        "key": "A",
        "title": "Demo: wrong number",
        "channel": "instagram",
        "caption": "GlowSerum hydration lasts 7 days.",
        "paid_gifted": False,
        "is_ai_media": False,
        "is_image_check": False,
    },
    {
        "key": "B",
        "title": "Demo: Marathi health claim",
        "channel": "instagram",
        "caption": "GlowSerum मुळे मुरुम पूर्णपणे बरे होतात.",
        "paid_gifted": False,
        "is_ai_media": False,
        "is_image_check": False,
    },
    {
        "key": "C",
        "title": "Demo: missing disclosure",
        "channel": "instagram",
        "caption": "GlowSerum is now available through our creator partnership.",
        "paid_gifted": True,
        "is_ai_media": False,
        "is_image_check": False,
    },
    {
        "key": "D",
        "title": "Demo: clean and approved",
        "channel": "instagram",
        "caption": "Enjoy a gentle daily ritual with GlowSerum.",
        "paid_gifted": False,
        "is_ai_media": False,
        "is_image_check": False,
    },
    {
        "key": "E",
        "title": "Demo: fresh findings",
        "channel": "instagram",
        "caption": "Yeh India ka number one serum hai!",
        "paid_gifted": False,
        "is_ai_media": False,
        "is_image_check": False,
    },
]

_provisioning_lock = asyncio.Lock()
_demo_ready = False


def is_demo_ready() -> bool:
    return _demo_ready


def set_demo_ready(ready: bool) -> None:
    global _demo_ready
    _demo_ready = ready


async def get_demo_workspace_id(db: Any) -> str | None:
    """Find the single workspace explicitly marked is_demo."""
    workspaces = (await db.scalars(select(Workspace))).all()
    for ws in workspaces:
        ws_settings = dict(ws.settings or {})
        if ws_settings.get("is_demo") is True:
            return ws.id
    return None


def _generate_demo_f_image_bytes() -> bytes:
    """Generate in-memory PNG for Draft F using Pillow."""
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (800, 520), "#F5F0EB")
        draw = ImageDraw.Draw(img)
        # Draw simulated cosmetic bottle
        draw.rounded_rectangle((320, 120, 470, 430), radius=24, fill="#E8C7B7", outline="#553B3B", width=5)
        draw.text((345, 260), "GlowSerum", fill="#553B3B")
        draw.text((25, 35), "GlowSerum Pure Radiance", fill="#322222")
        draw.text((20, 495), "100% Organic Extracts. Terms apply.", fill="#888888")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"


async def run_demo_startup_provisioning() -> None:
    """Entry point for app startup lifespan background task."""
    logger.info("Initializing demo workspace background provisioning...")
    try:
        await ensure_demo_workspace(
            sessions=SessionLocal,
            skip_creatives=True,
            reset_on_start=settings.demo_reset_on_start,
        )
        set_demo_ready(True)
        logger.info("Demo workspace is staged and ready for login.")
    except Exception as exc:
        logger.error(f"Demo workspace provisioning failed: {exc}", exc_info=True)


async def ensure_demo_workspace(
    sessions=SessionLocal,
    storage: Storage | None = None,
    upload_dir: str | Path | None = None,
    demo_password: str | None = None,
    admin_email: str | None = None,
    skip_creatives: bool = False,
    reset_on_start: bool = False,
) -> dict[str, Any]:
    """Idempotently stages the shared GlowSerum Demo workspace.

    Natural-key matching ensures running multiple times produces no duplicates.
    Never resets passwords of existing users; never alters existing user roles.
    """
    async with _provisioning_lock:
        active_storage = storage or get_storage()
        uploads = Path(upload_dir) if upload_dir is not None else Path(settings.upload_dir)

        # 1. Reset logic if requested: delete only the demo workspace
        if reset_on_start:
            async with sessions() as db:
                candidates = (await db.scalars(select(Workspace))).all()
                for cand in candidates:
                    cand_settings = dict(cand.settings or {})
                    is_demo = cand_settings.get("is_demo") is True
                    has_demo_user = await db.scalar(
                        select(User.id).where(
                            User.workspace_id == cand.id,
                            User.email.in_([
                                "creator@demo.local",
                                "demo-admin@glowserum.com",
                                "creator@glowserum.com",
                            ]),
                        ).limit(1)
                    )
                    if is_demo and has_demo_user:
                        logger.warning(f"Resetting existing demo workspace '{cand.name}' ({cand.id})...")
                        users_to_del = (await db.scalars(select(User).where(User.workspace_id == cand.id))).all()
                        for u in users_to_del:
                            await db.delete(u)
                        await db.delete(cand)
                        await db.commit()
                        break

        # 2. Locate or create the demo workspace
        demo_jobs_to_drain: list[str] = []
        workspace_id: str | None = None
        workspace: Workspace | None = None

        async with sessions() as db:
            # Check for existing workspace marked is_demo or containing demo users
            target_admin = (admin_email or settings.demo_admin_email).lower().strip()
            existing_user = await db.scalar(
                select(User).where(
                    User.email.in_([
                        target_admin,
                        "creator@demo.local",
                        "creator@glowserum.com",
                    ]),
                    User.is_active.is_(True),
                ).limit(1)
            )

            if existing_user:
                workspace = await db.get(Workspace, existing_user.workspace_id)
                if workspace:
                    workspace_id = workspace.id

            if not workspace:
                # Find any workspace marked is_demo
                workspaces = (await db.scalars(select(Workspace))).all()
                demo_ws = next((w for w in workspaces if dict(w.settings or {}).get("is_demo") is True), None)
                if demo_ws:
                    workspace_id = demo_ws.id
                    workspace = demo_ws
                else:
                    # Create new workspace
                    workspace = Workspace(
                        name="GlowSerum Demo",
                        settings={
                            "is_demo": True,
                            "india_pack_enabled": True,
                            "secret_terms": [],
                            "model_mode": "deterministic",
                            "brand_voice": [],
                        },
                    )
                    db.add(workspace)
                    await db.flush()
                    workspace_id = workspace.id

            # Ensure workspace has is_demo=True
            settings_data = dict(workspace.settings or {})
            settings_data["is_demo"] = True
            settings_data.setdefault("india_pack_enabled", True)
            settings_data.setdefault("secret_terms", [])
            settings_data.setdefault("model_mode", "deterministic")
            settings_data.setdefault("brand_voice", [])
            workspace.settings = settings_data

            # 3. Provision Admin User
            admin_user = await db.scalar(
                select(User).where(
                    User.workspace_id == workspace_id,
                    User.email == target_admin,
                )
            )
            if not admin_user:
                admin_pw = demo_password or secrets.token_urlsafe(32)
                admin_user = User(
                    workspace_id=workspace_id,
                    email=target_admin,
                    full_name="GlowSerum Demo Admin",
                    password_hash=hash_password(admin_pw),
                    role="admin",
                    is_active=True,
                )
                db.add(admin_user)
                await db.flush()

            # 4. Provision Demo Role Users (both @glowserum.com and @demo.local for CLI compatibility)
            role_specs = [
                # Web-accessible valid deliverable emails
                (settings.demo_admin_email, "GlowSerum Demo Admin", "admin"),
                ("creator@glowserum.com", "Demo Creator", "creator"),
                ("reviewer@glowserum.com", "Demo Reviewer", "reviewer"),
                ("manager@glowserum.com", "Demo Manager", "manager"),
                # CLI/regression backward-compatible emails
                ("creator@demo.local", "Demo Creator (Legacy)", "creator"),
                ("reviewer@demo.local", "Demo Reviewer (Legacy)", "reviewer"),
                ("manager@demo.local", "Demo Manager (Legacy)", "manager"),
            ]
            demo_user_map: dict[str, User] = {}
            for u_email, u_name, u_role in role_specs:
                u_obj = await db.scalar(
                    select(User).where(
                        User.workspace_id == workspace_id,
                        User.email == u_email,
                    )
                )
                if not u_obj:
                    pw = demo_password or secrets.token_urlsafe(32)
                    u_obj = User(
                        workspace_id=workspace_id,
                        email=u_email,
                        full_name=u_name,
                        password_hash=hash_password(pw),
                        role=u_role,
                        is_active=True,
                    )
                    db.add(u_obj)
                    await db.flush()
                demo_user_map[u_email] = u_obj

            # 5. Core Rules (IN-1..IN-6)
            for code, title, text, typ, severity in RULES:
                rule_row = await db.scalar(select(Rule).where(Rule.workspace_id == workspace_id, Rule.code == code, Rule.version == 1))
                if not rule_row:
                    rule_row = Rule(
                        workspace_id=workspace_id,
                        code=code,
                        title=title,
                        text=text,
                        type=typ,
                        severity=severity,
                        channels=[],
                        status="active",
                        version=1,
                        source_ref="India starter guidance; not legal advice. Fictional GlowSerum demo adaptation.",
                        created_by=admin_user.id,
                        confirmed_by=admin_user.id,
                    )
                    db.add(rule_row)
                    await db.flush()
                await ensure_rule_examples(db, rule_row)

            # Conflicting Rules for Guideline Health testing
            conflict_rules = [
                ("DEMO-CONFLICT-A", "Headlines must not use exclamation marks", "Headlines must not use exclamation marks.", "brand_voice", "advisory"),
                ("DEMO-CONFLICT-B", "Every headline must use an exclamation mark", "Every headline must use an exclamation mark.", "brand_voice", "advisory"),
            ]
            for code, title, text, typ, severity in conflict_rules:
                rule_row = await db.scalar(select(Rule).where(Rule.workspace_id == workspace_id, Rule.code == code, Rule.version == 1))
                if not rule_row:
                    rule_row = Rule(
                        workspace_id=workspace_id,
                        code=code,
                        title=title,
                        text=text,
                        type=typ,
                        severity=severity,
                        channels=["instagram"],
                        status="active",
                        version=1,
                        source_ref="Fictional demo conflicting rules for testing guideline health",
                        created_by=admin_user.id,
                        confirmed_by=admin_user.id,
                    )
                    db.add(rule_row)
                    await db.flush()
                await ensure_rule_examples(db, rule_row)

            # Additional planted guideline-health proof cases: four known conflicts
            # and four deliberately vague rules. All are fictional demo-only guidelines.
            planted_conflicts = [
                ("DEMO-CONFLICT-C", "Always include a price in paid-ad headlines", "Every paid-ad headline must display the current approved price."),
                ("DEMO-CONFLICT-D", "Never show prices in paid-ad headlines", "Every paid-ad headline must not display any price."),
                ("DEMO-CONFLICT-E", "Use only English on packaging", "All packaging copy must be written only in English."),
                ("DEMO-CONFLICT-F", "Packaging must be bilingual", "Every packaging panel must contain both English and Hindi copy."),
                ("DEMO-CONFLICT-G", "Always include a CTA in Instagram captions", "Every Instagram caption must end with a call to action."),
                ("DEMO-CONFLICT-H", "Never include a CTA in Instagram captions", "Instagram captions must not contain a call to action."),
            ]
            for code, title, text in planted_conflicts:
                rule_row = await db.scalar(select(Rule).where(Rule.workspace_id == workspace_id, Rule.code == code, Rule.version == 1))
                if not rule_row:
                    rule_row = Rule(workspace_id=workspace_id, code=code, title=title, text=text,
                        type="brand_voice", severity="advisory", channels=["paid_ad"] if "paid-ad" in text else (["packaging"] if "packaging" in text else ["instagram"]),
                        status="active", version=1, source_ref="Planted Phase 4 guideline-health conflict test case",
                        created_by=admin_user.id, confirmed_by=admin_user.id)
                    db.add(rule_row)
                    await db.flush()
                await ensure_rule_examples(db, rule_row)
            planted_vague = [
                ("DEMO-VAGUE-1", "Use appropriate product language", "Use appropriate product language in every campaign."),
                ("DEMO-VAGUE-2", "Maintain good quality visuals", "Maintain good quality visuals across social channels."),
                ("DEMO-VAGUE-3", "Keep the tone professional", "Keep the tone professional in all customer-facing copy."),
                ("DEMO-VAGUE-4", "Use suitable benefit descriptions", "Use suitable benefit descriptions on product pages."),
            ]
            for code, title, text in planted_vague:
                if not await db.scalar(select(Rule.id).where(Rule.workspace_id == workspace_id, Rule.code == code, Rule.version == 1)):
                    db.add(Rule(workspace_id=workspace_id, code=code, title=title, text=text,
                        type="brand_voice", severity="advisory", channels=[], status="active", version=1,
                        source_ref="Planted Phase 4 guideline-health vague-rule test case",
                        created_by=admin_user.id, confirmed_by=admin_user.id))

            # 6. Facts (including expired and expiring)
            facts = [
                ("FACT-RESULTS", "GlowSerum hydration duration", "4", "weeks", None, "2026-12-31T23:59:59+00:00", "Fictional product substantiation file v1"),
                ("FACT-OFFER", "GlowSerum launch offer ends, save/savings, discount, bundle and gift set", "15", "percent", "2026-10-01T00:00:00+00:00", "2026-10-31T23:59:59+00:00", "Fictional campaign offer calendar"),
                ("FACT-VOLUME", "GlowSerum bottle volume", "30", "ml", None, "2027-12-31T23:59:59+00:00", "Fictional approved product label"),
            ]
            for code, statement, value, unit, start, end, source in facts:
                if not await db.scalar(select(Fact.id).where(Fact.workspace_id == workspace_id, Fact.code == code, Fact.version == 1)):
                    parse = lambda x: datetime.fromisoformat(x) if x else None
                    db.add(Fact(
                        workspace_id=workspace_id,
                        code=code,
                        statement=statement,
                        value=value,
                        unit=unit,
                        valid_from=parse(start),
                        valid_to=parse(end),
                        source_ref=source,
                        version=1,
                        status="active",
                        created_by=admin_user.id,
                    ))

            expiring_valid_to = datetime.now(timezone.utc) + timedelta(days=3)
            if not await db.scalar(select(Fact.id).where(Fact.workspace_id == workspace_id, Fact.code == "FACT-DEMO-EXPIRING", Fact.version == 1)):
                db.add(Fact(
                    workspace_id=workspace_id,
                    code="FACT-DEMO-EXPIRING",
                    statement="GlowSerum holiday bonus gift voucher promotion",
                    value="500",
                    unit="INR",
                    valid_from=datetime.now(timezone.utc) - timedelta(days=27),
                    valid_to=expiring_valid_to,
                    source_ref="Fictional demo expiring promotion calendar",
                    version=1,
                    status="active",
                    created_by=admin_user.id,
                ))

            # 7. Brand Assets
            assets = [
                ("term_list", "GlowSerum banned terms", {"banned_terms": ["miracle", "cures acne", "zero risk"]}),
                ("palette", "GlowSerum approved palette", {"colors": ["#F3E8E1", "#C98E85", "#553B3B", "#FFFFFF"]}),
            ]
            for kind, name, data in assets:
                if not await db.scalar(select(BrandAsset.id).where(BrandAsset.workspace_id == workspace_id, BrandAsset.name == name)):
                    db.add(BrandAsset(workspace_id=workspace_id, kind=kind, name=name, data=data, created_by=admin_user.id))

            # 8. 52 Evaluation Posts
            if DATA.exists():
                posts = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]
                for post in posts:
                    campaign = "GlowSerum fictional evaluation set"
                    item = await db.scalar(select(ContentItem).where(ContentItem.workspace_id == workspace_id, ContentItem.title == post["title"], ContentItem.campaign == campaign))
                    if item:
                        continue
                    creative_filename = None
                    creative_storage_key = None
                    if not skip_creatives and post["expected_findings"] == ["visual"]:
                        try:
                            from PIL import Image, ImageDraw
                            folder = uploads / workspace_id / "creatives"
                            folder.mkdir(parents=True, exist_ok=True)
                            creative_filename = f"{post['id']}.png"
                            creative_storage_key = f"{workspace_id}/creatives/{creative_filename}"
                            image = Image.new("RGB", (800, 520), "#39FF14" if "neon green" in post["caption"].lower() else "#777777" if "low contrast" in post["caption"].lower() else "#2255AA" if "unapproved palette" in post["caption"].lower() else "#F5F0EB")
                            draw = ImageDraw.Draw(image)
                            if "low contrast" in post["caption"].lower():
                                draw.text((25, 35), "GlowSerum", fill="#777777")
                            else:
                                draw.text((25, 35), "GlowSerum", fill="#FFFFFF" if "neon green" in post["caption"].lower() else "#322222")
                            if "without the brand logo" not in post["caption"].lower():
                                draw.rounded_rectangle((320, 120, 470, 430), radius=24, fill="#E8C7B7", outline="#553B3B", width=5)
                                draw.text((345, 260), "GlowSerum", fill="#553B3B")
                            if "tiny unreadable" in post["caption"].lower():
                                draw.text((20, 495), "Terms apply. Results may vary.", fill="#888888")
                            image.save(uploads / creative_storage_key, format="PNG")
                        except ImportError:
                            creative_filename = None
                            creative_storage_key = None
                    item = ContentItem(workspace_id=workspace_id, title=post["title"], channel=post["channel"], campaign=campaign, status="draft", current_revision=1, created_by=admin_user.id)
                    db.add(item)
                    await db.flush()
                    db.add(ContentRevision(
                        workspace_id=workspace_id,
                        content_id=item.id,
                        version=1,
                        caption=post["caption"],
                        alt_text=post["alt_text"],
                        is_ai_media=post["is_ai_media"],
                        paid_gifted=post["id"] in PAID_GIFTED_DECLARATION_POST_IDS,
                        detected_language="en",
                        creative_filename=creative_filename,
                        creative_storage_key=creative_storage_key,
                        created_by=admin_user.id,
                    ))

            # 9. Demo Drafts A through F under "GlowSerum DEMO"
            creator_author = demo_user_map.get("creator@glowserum.com") or demo_user_map.get("creator@demo.local") or admin_user
            for draft_spec in DEMO_DRAFTS:
                demo_item = await db.scalar(
                    select(ContentItem).where(
                        ContentItem.workspace_id == workspace_id,
                        ContentItem.campaign == "GlowSerum DEMO",
                        ContentItem.title == draft_spec["title"],
                    )
                )
                creative_fn = None
                creative_key = None

                # For Draft F, ensure the image is in storage
                if draft_spec.get("is_image_check"):
                    creative_fn = "demo_f_image.png"
                    creative_key = f"{workspace_id}/creatives/{creative_fn}"
                    needs_put = True
                    try:
                        existing_bytes = active_storage.get_bytes(creative_key)
                        if len(existing_bytes) > 0:
                            needs_put = False
                    except Exception:
                        needs_put = True
                    if needs_put:
                        img_bytes = _generate_demo_f_image_bytes()
                        active_storage.put_bytes(creative_key, img_bytes, "image/png")

                if not demo_item:
                    demo_item = ContentItem(
                        workspace_id=workspace_id,
                        title=draft_spec["title"],
                        channel=draft_spec["channel"],
                        campaign="GlowSerum DEMO",
                        status="draft",
                        current_revision=1,
                        created_by=creator_author.id,
                    )
                    db.add(demo_item)
                    await db.flush()

                    demo_rev = ContentRevision(
                        workspace_id=workspace_id,
                        content_id=demo_item.id,
                        version=1,
                        caption=draft_spec["caption"],
                        alt_text=None,
                        is_ai_media=draft_spec["is_ai_media"],
                        paid_gifted=draft_spec["paid_gifted"],
                        detected_language="mr" if draft_spec["key"] == "B" else "en",
                        creative_filename=creative_fn,
                        creative_storage_key=creative_key,
                        created_by=creator_author.id,
                    )
                    db.add(demo_rev)
                    await db.flush()
                else:
                    demo_rev = await db.scalar(
                        select(ContentRevision).where(
                            ContentRevision.content_id == demo_item.id,
                            ContentRevision.version == demo_item.current_revision,
                        )
                    )
                    # If Draft F revision was missing creative_storage_key, attach it
                    if draft_spec.get("is_image_check") and not demo_rev.creative_storage_key:
                        demo_rev.creative_filename = creative_fn
                        demo_rev.creative_storage_key = creative_key

                # Check if analysis job needs to be enqueued
                existing_job = await db.scalar(
                    select(ReviewJob).where(
                        ReviewJob.content_id == demo_item.id,
                        ReviewJob.revision_id == demo_rev.id,
                        ReviewJob.status == "completed",
                    )
                )
                if not existing_job:
                    job = await enqueue_review_job(db, creator_author, demo_item, demo_rev)
                    demo_jobs_to_drain.append(job.id)

            await db.commit()

        # 10. Drain the durable worker outside open transaction
        for _ in demo_jobs_to_drain:
            await process_next_job(sessions=sessions, worker_id="demo-provisioning-worker")

        # 11. Post-analysis workflows (Approval for Draft D, Precedent for Draft A)
        failures: list[str] = []
        draft_statuses: dict[str, str] = {}

        async with sessions() as db:
            creator_u = await db.scalar(select(User).where(User.workspace_id == workspace_id, User.email.in_(["creator@glowserum.com", "creator@demo.local"])))
            reviewer_u = await db.scalar(select(User).where(User.workspace_id == workspace_id, User.email.in_(["reviewer@glowserum.com", "reviewer@demo.local"])))
            manager_u = await db.scalar(select(User).where(User.workspace_id == workspace_id, User.email.in_(["manager@glowserum.com", "manager@demo.local"])))

            # Inspect review jobs for all demo drafts
            for spec in DEMO_DRAFTS:
                item = await db.scalar(
                    select(ContentItem).where(
                        ContentItem.workspace_id == workspace_id,
                        ContentItem.campaign == "GlowSerum DEMO",
                        ContentItem.title == spec["title"],
                    )
                )
                if not item:
                    continue
                job = await db.scalar(
                    select(ReviewJob).where(
                        ReviewJob.content_id == item.id,
                        ReviewJob.workspace_id == workspace_id,
                    ).order_by(ReviewJob.created_at.desc()).limit(1)
                )
                status = job.status if job else "unknown"
                draft_statuses[spec["title"]] = status
                if status != "completed":
                    failures.append(f"Draft '{spec['title']}' review job is '{status}' (error: {job.error if job else 'none'})")

            # Approval: Draft D
            item_d = await db.scalar(
                select(ContentItem).where(
                    ContentItem.workspace_id == workspace_id,
                    ContentItem.campaign == "GlowSerum DEMO",
                    ContentItem.title == "Demo: clean and approved",
                )
            )
            if item_d and item_d.status != "approved" and creator_u and reviewer_u and manager_u:
                await change_workflow(item_d.id, StateInput(action="submit"), creator_u, db)
                await change_workflow(item_d.id, StateInput(action="start_review"), reviewer_u, db)
                await change_workflow(item_d.id, StateInput(action="approve"), manager_u, db)

            # Precedent: Draft A
            item_a = await db.scalar(
                select(ContentItem).where(
                    ContentItem.workspace_id == workspace_id,
                    ContentItem.campaign == "GlowSerum DEMO",
                    ContentItem.title == "Demo: wrong number",
                )
            )
            if item_a and reviewer_u:
                finding_a = await db.scalar(
                    select(ClaimFinding).where(
                        ClaimFinding.content_id == item_a.id,
                        ClaimFinding.workspace_id == workspace_id,
                    ).order_by(ClaimFinding.id).limit(1)
                )
                if finding_a:
                    existing_decision = await db.scalar(
                        select(FindingDecision.id).where(
                            FindingDecision.finding_id == finding_a.id,
                            FindingDecision.workspace_id == workspace_id,
                            FindingDecision.action == "dispute",
                        )
                    )
                    if not existing_decision:
                        await decide_finding(
                            finding_a.id,
                            DecisionInput(
                                action="dispute",
                                reason="Dispute recorded for demo: 7-day hydration surge tested in internal study",
                            ),
                            BackgroundTasks(),
                            reviewer_u,
                            db,
                        )

                    existing_precedent = await db.scalar(
                        select(Precedent.id).where(
                            Precedent.finding_id == finding_a.id,
                            Precedent.workspace_id == workspace_id,
                        )
                    )
                    if not existing_precedent:
                        created_precedent = await create_precedent(
                            PrecedentInput(
                                finding_id=finding_a.id,
                                channel="instagram",
                                pattern_text="GlowSerum hydration lasts 7 days.",
                                reason="Dispute recorded for demo: 7-day hydration surge tested in internal study",
                            ),
                            reviewer_u,
                            db,
                        )
                        existing_precedent = created_precedent["id"]
                    # The demo workspace explicitly shows the complete reviewer →
                    # owner approval lifecycle. Production precedents remain pending
                    # until a manager/admin approves them in the ledger.
                    demo_precedent = await db.scalar(select(Precedent).where(
                        Precedent.id == existing_precedent,
                        Precedent.workspace_id == workspace_id,
                    ))
                    if demo_precedent and demo_precedent.status == "pending" and manager_u:
                        await approve_precedent(demo_precedent.id, manager_u, db)

            set_demo_ready(True)

            return {
                "workspace_id": workspace_id,
                "demo_mode": True,
                "drafts": [
                    {"title": title, "job_status": status}
                    for title, status in draft_statuses.items()
                ],
                "failures": failures,
            }
