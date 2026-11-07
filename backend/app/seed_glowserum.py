"""Seed fictional GlowSerum facts, rules, assets, 40 evaluation posts, and optional demo workspace.
Run after migrations: python -m app.seed_glowserum --email admin@example.com
Demo mode: python -m app.seed_glowserum --email admin@example.com --skip-creatives --demo --demo-password <password>
"""
import argparse, asyncio, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select
from fastapi import BackgroundTasks

from app.db.session import SessionLocal
from app.core.config import settings
from app.core.security import hash_password
from app.models.entities import (
    User,
    Workspace,
    Rule,
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
from app.api.intelligence import create_precedent, PrecedentInput

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data' / 'sample' / 'glowserum_40_posts.jsonl'
PAID_GIFTED_DECLARATION_POST_IDS = {"GC-021", "GC-022", "GC-023", "GC-024", "GC-025"}

RULES = [
    ('IN-1', 'Substantiation for factual claims', 'Factual, measurable, comparative or performance claims must have a traceable approved source. If no source is found, request human review; do not infer that the claim is false.', 'required_text', 'advisory'),
    ('IN-2', 'Superlatives require proof', 'Claims using best, only, #1, number one or equivalent superlatives require specific, current evidence.', 'pattern', 'critical'),
    ('IN-3', 'Disclaimer cannot cure misleading main claim', 'A disclaimer must not contradict or attempt to cure a misleading main claim. Flag absolute promises alongside disclaimer language for human review.', 'disclosure', 'critical'),
    ('IN-4', 'Paid or gifted disclosure', 'Paid or gifted creator content must use a clear disclosure such as #ad or Paid partnership, subject to current platform guidance.', 'disclosure', 'major'),
    ('IN-5', 'Restricted cure and guaranteed-result wording', 'Cure or guaranteed-result wording for health and skin products must be routed for human/legal review. This is not a legal determination.', 'term', 'critical'),
    ('IN-6', 'AI-generated media declaration', 'Realistic AI-generated image/video may require a platform label. This is an advisory reminder; check current platform policy.', 'disclosure', 'advisory'),
]

DEMO_DRAFTS = [
    {
        "key": "A",
        "title": "Demo: wrong number",
        "channel": "instagram",
        "caption": "GlowSerum hydration lasts 7 days.",
        "paid_gifted": False,
        "is_ai_media": False,
    },
    {
        "key": "B",
        "title": "Demo: Marathi health claim",
        "channel": "instagram",
        "caption": "GlowSerum मुळे मुरुम पूर्णपणे बरे होतात.",
        "paid_gifted": False,
        "is_ai_media": False,
    },
    {
        "key": "C",
        "title": "Demo: missing disclosure",
        "channel": "instagram",
        "caption": "GlowSerum is now available through our creator partnership.",
        "paid_gifted": True,
        "is_ai_media": False,
    },
    {
        "key": "D",
        "title": "Demo: clean and approved",
        "channel": "instagram",
        "caption": "Enjoy a gentle daily ritual with GlowSerum.",
        "paid_gifted": False,
        "is_ai_media": False,
    },
    {
        "key": "E",
        "title": "Demo: fresh findings",
        "channel": "instagram",
        "caption": "Yeh India ka number one serum hai!",
        "paid_gifted": False,
        "is_ai_media": False,
    },
]


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

    uploads = Path(upload_dir) if upload_dir is not None else Path(settings.upload_dir)

    async with sessions() as db:
        user = await db.scalar(select(User).where(User.email == email.lower().strip(), User.is_active.is_(True)))
        if not user:
            raise SystemExit(f'No active user found for {email}. Register/login to create a workspace first.')
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
            exists = await db.scalar(select(Rule.id).where(Rule.workspace_id == workspace_id, Rule.code == code, Rule.version == 1))
            if not exists:
                db.add(Rule(
                    workspace_id=workspace_id,
                    code=code,
                    title=title,
                    text=text,
                    type=typ,
                    severity=severity,
                    channels=[],
                    status='active',
                    version=1,
                    source_ref='India starter guidance; not legal advice. Fictional GlowSerum demo adaptation; verify current regulations and platform rules.',
                    created_by=user.id,
                    confirmed_by=user.id,
                ))

        facts = [
            ('FACT-RESULTS', 'GlowSerum hydration duration', '4', 'weeks', None, '2026-12-31T23:59:59+00:00', 'Fictional product substantiation file v1'),
            ('FACT-OFFER', 'GlowSerum launch offer ends, save/savings, discount, bundle and gift set', '15', 'percent', '2026-10-01T00:00:00+00:00', '2026-10-31T23:59:59+00:00', 'Fictional campaign offer calendar'),
            ('FACT-VOLUME', 'GlowSerum bottle volume', '30', 'ml', None, '2027-12-31T23:59:59+00:00', 'Fictional approved product label'),
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
                    status='active',
                    created_by=user.id,
                ))

        assets = [
            ('term_list', 'GlowSerum banned terms', {'banned_terms': ['miracle', 'cures acne', 'zero risk']}),
            ('palette', 'GlowSerum approved palette', {'colors': ['#F3E8E1', '#C98E85', '#553B3B', '#FFFFFF']}),
        ]
        for kind, name, data in assets:
            if not await db.scalar(select(BrandAsset.id).where(BrandAsset.workspace_id == workspace_id, BrandAsset.name == name)):
                db.add(BrandAsset(workspace_id=workspace_id, kind=kind, name=name, data=data, created_by=user.id))

        posts = [json.loads(line) for line in DATA.read_text(encoding='utf-8').splitlines() if line.strip()]
        created = 0
        for post in posts:
            campaign = 'GlowSerum fictional evaluation set'
            item = await db.scalar(select(ContentItem).where(ContentItem.workspace_id == workspace_id, ContentItem.title == post['title'], ContentItem.campaign == campaign))
            if item:
                continue
            creative_filename = None
            creative_storage_key = None
            if not skip_creatives and post['expected_findings'] == ['visual']:
                try:
                    from PIL import Image, ImageDraw
                    folder = uploads / workspace_id / 'creatives'
                    folder.mkdir(parents=True, exist_ok=True)
                    creative_filename = f"{post['id']}.png"
                    creative_storage_key = f"{workspace_id}/creatives/{creative_filename}"
                    image = Image.new('RGB', (800, 520), '#39FF14' if 'neon green' in post['caption'].lower() else '#777777' if 'low contrast' in post['caption'].lower() else '#2255AA' if 'unapproved palette' in post['caption'].lower() else '#F5F0EB')
                    draw = ImageDraw.Draw(image)
                    if 'low contrast' in post['caption'].lower():
                        draw.text((25, 35), 'GlowSerum', fill='#777777')
                    else:
                        draw.text((25, 35), 'GlowSerum', fill='#FFFFFF' if 'neon green' in post['caption'].lower() else '#322222')
                    if 'without the brand logo' not in post['caption'].lower():
                        draw.rounded_rectangle((320, 120, 470, 430), radius=24, fill='#E8C7B7', outline='#553B3B', width=5)
                        draw.text((345, 260), 'GlowSerum', fill='#553B3B')
                    if 'tiny unreadable' in post['caption'].lower():
                        draw.text((20, 495), 'Terms apply. Results may vary.', fill='#888888')
                    image.save(uploads / creative_storage_key, format='PNG')
                except ImportError:
                    creative_filename = None
                    creative_storage_key = None
            item = ContentItem(workspace_id=workspace_id, title=post['title'], channel=post['channel'], campaign=campaign, status='draft', current_revision=1, created_by=user.id)
            db.add(item)
            await db.flush()
            db.add(ContentRevision(
                workspace_id=workspace_id,
                content_id=item.id,
                version=1,
                caption=post['caption'],
                alt_text=post['alt_text'],
                is_ai_media=post['is_ai_media'],
                paid_gifted=post['id'] in PAID_GIFTED_DECLARATION_POST_IDS,
                detected_language='en',
                creative_filename=creative_filename,
                creative_storage_key=creative_storage_key,
                created_by=user.id,
            ))
            created += 1

        demo_jobs_to_drain = []
        if demo:
            # 1. Users
            demo_users_spec = [
                ("creator@demo.local", "Demo Creator", "creator"),
                ("reviewer@demo.local", "Demo Reviewer", "reviewer"),
                ("manager@demo.local", "Demo Manager", "manager"),
            ]
            demo_users = {}
            for u_email, u_name, u_role in demo_users_spec:
                existing_u = await db.scalar(select(User).where(User.workspace_id == workspace_id, User.email == u_email))
                if not existing_u:
                    existing_u = User(
                        workspace_id=workspace_id,
                        email=u_email,
                        full_name=u_name,
                        password_hash=hash_password(demo_password),
                        role=u_role,
                        is_active=True,
                    )
                    db.add(existing_u)
                    await db.flush()
                demo_users[u_role] = existing_u

            # 2. Facts
            expiring_valid_to = datetime.now(timezone.utc) + timedelta(days=3)
            if not await db.scalar(select(Fact.id).where(Fact.workspace_id == workspace_id, Fact.code == 'FACT-DEMO-EXPIRING', Fact.version == 1)):
                db.add(Fact(
                    workspace_id=workspace_id,
                    code='FACT-DEMO-EXPIRING',
                    statement='GlowSerum holiday bonus gift voucher promotion',
                    value='500',
                    unit='INR',
                    valid_from=datetime.now(timezone.utc) - timedelta(days=27),
                    valid_to=expiring_valid_to,
                    source_ref='Fictional demo expiring promotion calendar',
                    version=1,
                    status='active',
                    created_by=user.id,
                ))

            # 3. Rules
            conflict_rules = [
                ('DEMO-CONFLICT-A', 'Never use exclamation marks in headlines', 'Never use exclamation marks in headlines', 'brand_voice', 'advisory'),
                ('DEMO-CONFLICT-B', 'Use an exclamation mark in every headline', 'Use an exclamation mark in every headline', 'brand_voice', 'advisory'),
            ]
            for code, title, text, typ, severity in conflict_rules:
                if not await db.scalar(select(Rule.id).where(Rule.workspace_id == workspace_id, Rule.code == code, Rule.version == 1)):
                    db.add(Rule(
                        workspace_id=workspace_id,
                        code=code,
                        title=title,
                        text=text,
                        type=typ,
                        severity=severity,
                        channels=['instagram'],
                        status='active',
                        version=1,
                        source_ref='Fictional demo conflicting rules for testing guideline health',
                        created_by=user.id,
                        confirmed_by=user.id,
                    ))

            # 4. Content drafts under campaign 'GlowSerum DEMO'
            creator_u = demo_users['creator']
            for draft_spec in DEMO_DRAFTS:
                demo_item = await db.scalar(
                    select(ContentItem).where(
                        ContentItem.workspace_id == workspace_id,
                        ContentItem.campaign == "GlowSerum DEMO",
                        ContentItem.title == draft_spec["title"],
                    )
                )
                if not demo_item:
                    demo_item = ContentItem(
                        workspace_id=workspace_id,
                        title=draft_spec["title"],
                        channel=draft_spec["channel"],
                        campaign="GlowSerum DEMO",
                        status="draft",
                        current_revision=1,
                        created_by=creator_u.id,
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
                        created_by=creator_u.id,
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

                # 5. Analysis: enqueue review job if none exists
                existing_job = await db.scalar(
                    select(ReviewJob).where(
                        ReviewJob.content_id == demo_item.id,
                        ReviewJob.revision_id == demo_rev.id,
                        ReviewJob.status == "completed",
                    )
                )
                if not existing_job:
                    job = await enqueue_review_job(db, creator_u, demo_item, demo_rev)
                    demo_jobs_to_drain.append((draft_spec["key"], draft_spec["title"], job.id))

        await db.commit()

        if not demo:
            print(json.dumps({'workspace_id': workspace_id, 'rules_seeded': len(RULES), 'evaluation_posts_in_file': len(posts), 'new_content_items_created': created, 'fictional_data': True}, indent=2))
            return

    # Drain the durable review-job worker outside the open transaction
    for _ in demo_jobs_to_drain:
        await process_next_job(sessions=sessions, worker_id="demo-seed-worker")

    # Post-analysis workflows (Approval for D, Precedent for A) in second session
    failures = []
    draft_statuses = {}

    async with sessions() as db:
        user = await db.scalar(select(User).where(User.email == email.lower().strip(), User.is_active.is_(True)))
        workspace_id = user.workspace_id

        creator_u = await db.scalar(select(User).where(User.workspace_id == workspace_id, User.email == "creator@demo.local"))
        reviewer_u = await db.scalar(select(User).where(User.workspace_id == workspace_id, User.email == "reviewer@demo.local"))
        manager_u = await db.scalar(select(User).where(User.workspace_id == workspace_id, User.email == "manager@demo.local"))

        # Inspect review jobs for each demo draft
        for spec in DEMO_DRAFTS:
            item = await db.scalar(
                select(ContentItem).where(
                    ContentItem.workspace_id == workspace_id,
                    ContentItem.campaign == "GlowSerum DEMO",
                    ContentItem.title == spec["title"],
                )
            )
            job = await db.scalar(
                select(ReviewJob).where(
                    ReviewJob.content_id == item.id,
                    ReviewJob.workspace_id == workspace_id,
                ).order_by(ReviewJob.created_at.desc()).limit(1)
            )
            job_status = job.status if job else "unknown"
            draft_statuses[spec["title"]] = job_status
            if job_status != "completed":
                failures.append(f"Draft '{spec['title']}' review job status is '{job_status}' (error: {job.error if job else 'none'})")

        # 6. Approval: take D through submit, review, and approve
        item_d = await db.scalar(
            select(ContentItem).where(
                ContentItem.workspace_id == workspace_id,
                ContentItem.campaign == "GlowSerum DEMO",
                ContentItem.title == "Demo: clean and approved",
            )
        )
        if item_d and item_d.status != "approved":
            await change_workflow(item_d.id, StateInput(action='submit'), creator_u, db)
            await change_workflow(item_d.id, StateInput(action='start_review'), reviewer_u, db)
            await change_workflow(item_d.id, StateInput(action='approve'), manager_u, db)

        # 7. Precedent: for one finding on A, record a dispute and create Precedent
        item_a = await db.scalar(
            select(ContentItem).where(
                ContentItem.workspace_id == workspace_id,
                ContentItem.campaign == "GlowSerum DEMO",
                ContentItem.title == "Demo: wrong number",
            )
        )
        if item_a:
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
                    await create_precedent(
                        PrecedentInput(
                            finding_id=finding_a.id,
                            channel="instagram",
                            pattern_text="GlowSerum hydration lasts 7 days.",
                            reason="Dispute recorded for demo: 7-day hydration surge tested in internal study",
                        ),
                        reviewer_u,
                        db,
                    )

        summary = {
            "workspace_id": workspace_id,
            "demo_mode": True,
            "users": [
                {"email": u.email, "role": u.role}
                for u in [creator_u, reviewer_u, manager_u]
                if u is not None
            ],
            "drafts": [
                {"title": title, "job_status": status}
                for title, status in draft_statuses.items()
            ],
            "failures": failures,
        }
        print(json.dumps(summary, indent=2))

        if failures:
            raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', required=True)
    parser.add_argument('--skip-creatives', action='store_true', help='Skip writing creative image files and leave creative filename/storage key as None')
    parser.add_argument('--demo', action='store_true', help='Seed demo workspace with extra roles, conflict rules, expiring facts, and 5 demo drafts')
    parser.add_argument('--demo-password', help='Password for creator@demo.local, reviewer@demo.local, manager@demo.local')
    args = parser.parse_args()

    if args.demo and not args.demo_password:
        parser.error("--demo-password is required when --demo is set")

    asyncio.run(seed(
        args.email,
        skip_creatives=args.skip_creatives,
        demo=args.demo,
        demo_password=args.demo_password,
    ))
