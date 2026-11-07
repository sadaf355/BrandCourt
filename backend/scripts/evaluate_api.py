"""Capture reproducible, durable-worker predictions for one evaluation variant."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "data" / "sample" / "glowserum_40_posts.jsonl"
VARIANTS = {"code_rules_only", "retrieval_and_nli", "full_pipeline"}


def labels_for(result):
    labels = set()
    for finding in result.get("findings", []):
        verdict = finding.get("verdict")
        method = finding.get("analysis_method", "")
        evidence = finding.get("evidence", [])
        codes = {str(entry.get("code", "")) for entry in evidence}
        types = {str(entry.get("type", "")) for entry in evidence}
        if "IN-2" in codes:
            labels.add("unsupported_superlative")
        if "IN-5" in codes:
            labels.add("restricted_health_claim")
        if "brand_term_list" in types:
            labels.add("banned_term")
        if "IN-4" in codes:
            labels.add("missing_disclosure")
        if verdict == "outdated":
            labels.add("expired_fact")
        if verdict == "contradicted":
            labels.add("wrong_number")
        if method == "image_intelligence_v1" or "visual_check" in types:
            labels.add("visual")
    return sorted(labels)


def source_metrics(result):
    findings = result.get("findings", [])
    errors = [
        finding
        for finding in findings
        if finding.get("verdict") in {"unsupported", "contradicted", "outdated"}
    ]
    valid_source_errors = sum(
        any(
            evidence.get("source_ref")
            and evidence.get("type") in {"fact", "approved_fact", "active_rule"}
            and str(evidence["source_ref"]).strip().lower() not in {"unknown", "n/a", "none"}
            for evidence in finding.get("evidence", [])
        )
        for finding in errors
    )
    return {
        "error_findings": len(errors),
        "valid_source_error_findings": valid_source_errors,
        "needs_human_review_count": sum(
            finding.get("verdict") == "needs_human_review" for finding in findings
        ),
        "findings": findings,
    }


async def ollama_preflight(base_url: str, *model_names: str) -> None:
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(base_url.rstrip("/") + "/api/tags")
        response.raise_for_status()
    models = response.json().get("models", [])
    available = {
        model.get("name")
        for model in models
        if isinstance(model, dict) and isinstance(model.get("name"), str)
    }
    missing = sorted(set(model_names) - available)
    if missing:
        raise RuntimeError(
            f"required model(s) {missing!r} are not present; available models: "
            f"{sorted(available)}"
        )


def worker_elapsed_ms(job):
    if not job.get("started_at") or not job.get("finished_at"):
        return None
    started = datetime.fromisoformat(job["started_at"])
    finished = datetime.fromisoformat(job["finished_at"])
    return round((finished - started).total_seconds() * 1000, 2)


async def main(args):
    if args.variant not in VARIANTS:
        raise ValueError(f"Unknown evaluation variant: {args.variant}")
    gold_bytes = GOLD.read_bytes()
    gold = [json.loads(line) for line in gold_bytes.decode("utf-8").splitlines() if line.strip()]
    dataset_sha256 = hashlib.sha256(gold_bytes).hexdigest()

    if args.variant in {"retrieval_and_nli", "full_pipeline"}:
        try:
            await ollama_preflight(
                args.ollama_base_url,
                args.ollama_model,
                args.ollama_embedding_model,
            )
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            print(json.dumps({
                "status": "blocked",
                "variant": args.variant,
                "reason": f"Ollama preflight failed: {exc}",
                "predictions_written": False,
            }, indent=2))
            raise SystemExit(2) from exc

    headers = {"Authorization": f"Bearer {args.token}"}
    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/") + "/api",
        headers=headers,
        timeout=40,
    ) as client:
        response = await client.get("/content")
        response.raise_for_status()
        items = [
            item for item in response.json()
            if item.get("campaign") == "GlowSerum fictional evaluation set"
        ]
        items_by_title = {item["title"]: item for item in items}
        predictions = []
        for row in gold:
            job = None
            failure = None
            item = items_by_title.get(row["title"])
            try:
                if item is None:
                    raise RuntimeError("Seeded evaluation content is missing.")
                queued = await client.post(
                    f"/content/{item['id']}/analyze",
                    params={"evaluation_variant": args.variant},
                )
                queued.raise_for_status()
                job_id = queued.json()["job_id"]
                for _ in range(180):
                    check = await client.get(f"/jobs/{job_id}")
                    check.raise_for_status()
                    job = check.json()
                    if job["status"] in {"completed", "failed"}:
                        break
                    await asyncio.sleep(0.5)
                if not job or job["status"] != "completed":
                    failure = job.get("error") if job else "Job did not return a status."
                elif (job.get("result") or {}).get("evaluation_variant") != args.variant:
                    failure = "Worker result did not confirm the requested evaluation variant."
            except (httpx.HTTPError, KeyError, RuntimeError) as exc:
                failure = f"{type(exc).__name__}: {exc}"

            result = (job or {}).get("result") or {}
            completed = failure is None
            predictions.append({
                "id": row["id"],
                "variant": args.variant,
                "dataset_sha256": dataset_sha256,
                "status": "completed" if completed else "failed",
                "failure": failure,
                "predicted_findings": labels_for(result) if completed else [],
                "elapsed_ms": worker_elapsed_ms(job) if completed else None,
                **(
                    source_metrics(result)
                    if completed
                    else {
                        "error_findings": 0,
                        "valid_source_error_findings": 0,
                        "needs_human_review_count": 0,
                        "findings": [],
                    }
                ),
            })
            print(f"{row['id']} {row['title']}: {failure or predictions[-1]['predicted_findings']}")

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in predictions) + "\n",
        encoding="utf-8",
    )
    failed = sum(row["status"] != "completed" for row in predictions)
    print(json.dumps({
        "status": "completed" if failed == 0 else "completed_with_failures",
        "variant": args.variant,
        "dataset_sha256": dataset_sha256,
        "expected_cases": len(gold),
        "seeded_items_found": len(items),
        "completed_cases": len(gold) - failed,
        "failed_cases": failed,
        "predictions_file": str(output),
        "latency_measure": "worker started_at to finished_at, milliseconds",
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    parser.add_argument(
        "--ollama-base-url",
        default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    )
    parser.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", "llama3.2:3b"))
    parser.add_argument(
        "--ollama-embedding-model",
        default=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
    )
    parser.add_argument("--out")
    arguments = parser.parse_args()
    arguments.out = arguments.out or str(
        ROOT / "data" / "sample" / f"glowserum_{arguments.variant}_predictions.jsonl"
    )
    asyncio.run(main(arguments))
