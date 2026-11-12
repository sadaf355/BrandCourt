"""Seed fictional GlowSerum facts, rules, assets, 40 evaluation posts, and optional demo workspace.
Run after migrations: python -m app.seed_glowserum --email admin@example.com
Demo mode: python -m app.seed_glowserum --email admin@example.com --skip-creatives --demo --demo-password <password>
"""
import argparse, asyncio, json
from datetime import datetime
from pathlib import Path
from sqlalchemy import select

from app.db.session import SessionLocal
from app.core.config import settings
from app.models.entities import (
    User,
    Workspace,
    Rule,
    Fact,
    BrandAsset,
    ContentItem,
    ContentRevision,
)
from app.services.demo_workspace import ensure_demo_workspace, ensure_rule_examples, RULES

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "sample" / "glowserum_40_posts.jsonl"
PAID_GIFTED_DECLARATION_POST_IDS = {"GC-021", "GC-022", "GC-023", "GC-024", "GC-025"}


async def seed(
    email: str,
    sessions=SessionLocal,
    upload_dir: str | Path | None = None,
    skip_creatives: bool = False,
    demo: bool = False,
    demo_password: str | None = None,
):
    if demo and not demo_password:
        raise ValueError("--demo-password is required when --demo is set")

    if demo:
        result = await ensure_demo_workspace(
            sessions=sessions,
            upload_dir=upload_dir,
            skip_creatives=skip_creatives,
            demo_password=demo_password,
            admin_email=email,
        )
        print(json.dumps(result, indent=2))
        if result.get("failures"):
            raise SystemExit(1)
        return

    # Normal (non-demo) seed path
    uploads = Path(upload_dir) if upload_dir is not None else Path(settings.upload_dir)

    async with sessions() as db:
        user = await db.scalar(select(User).where(User.email == email.lower().strip(), User.is_active.is_(True)))
        if not user:
            raise SystemExit(f"No active user found for {email}. Register/login to create a workspace first.")
        workspace_id = user.workspace_id
        workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
        if workspace:
            settings_data = dict(workspace.settings or {})
            settings_data.setdefault("india_pack_enabled", True)
            settings_data.setdefault("secret_terms", [])
            settings_data.setdefault("model_mode", "deterministic")
            settings_data.setdefault("brand_voice", [])
            workspace.settings = settings_data

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
                    source_ref="India starter guidance; not legal advice. Fictional GlowSerum demo adaptation; verify current regulations and platform rules.",
                    created_by=user.id,
                    confirmed_by=user.id,
                )
                db.add(rule_row)
                await db.flush()
            await ensure_rule_examples(db, rule_row)

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
                    created_by=user.id,
                ))

        assets = [
            ("term_list", "GlowSerum banned terms", {"banned_terms": ["miracle", "cures acne", "zero risk"]}),
            ("palette", "GlowSerum approved palette", {"colors": ["#F3E8E1", "#C98E85", "#553B3B", "#FFFFFF"]}),
        ]
        for kind, name, data in assets:
            if not await db.scalar(select(BrandAsset.id).where(BrandAsset.workspace_id == workspace_id, BrandAsset.name == name)):
                db.add(BrandAsset(workspace_id=workspace_id, kind=kind, name=name, data=data, created_by=user.id))

        posts = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]
        created = 0
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
            item = ContentItem(workspace_id=workspace_id, title=post["title"], channel=post["channel"], campaign=campaign, status="draft", current_revision=1, created_by=user.id)
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
                created_by=user.id,
            ))
            created += 1

        await db.commit()
        print(json.dumps({"workspace_id": workspace_id, "rules_seeded": len(RULES), "evaluation_posts_in_file": len(posts), "new_content_items_created": created, "fictional_data": True}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--skip-creatives", action="store_true", help="Skip writing creative image files and leave creative filename/storage key as None")
    parser.add_argument("--demo", action="store_true", help="Seed demo workspace with extra roles, conflict rules, expiring facts, and 5 demo drafts")
    parser.add_argument("--demo-password", help="Password for creator@demo.local, reviewer@demo.local, manager@demo.local")
    args = parser.parse_args()

    if args.demo and not args.demo_password:
        parser.error("--demo-password is required when --demo is set")

    asyncio.run(seed(
        args.email,
        skip_creatives=args.skip_creatives,
        demo=args.demo,
        demo_password=args.demo_password,
    ))
