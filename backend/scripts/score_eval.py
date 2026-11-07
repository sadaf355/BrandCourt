"""Score recorded Claim Court outputs against the labelled sample set.

Prediction rows are produced by ``evaluate_api.py`` and retain measured timings,
source evidence, and needs-human-review counts. Missing rows count as no findings.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "data" / "sample" / "glowserum_40_posts.jsonl"


def load(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def score(gold: list[dict], predictions: list[dict]) -> dict[str, Any]:
    gold_ids = [row["id"] for row in gold]
    prediction_ids = [row["id"] for row in predictions]
    if len(set(gold_ids)) != len(gold_ids):
        raise ValueError("Gold case IDs must be unique.")
    if len(set(prediction_ids)) != len(prediction_ids):
        raise ValueError("Prediction case IDs must be unique.")
    unknown_ids = sorted(set(prediction_ids) - set(gold_ids))
    if unknown_ids:
        raise ValueError(f"Predictions contain unknown case IDs: {unknown_ids}")

    pred_by_id = {
        row["id"]: set(row.get("predicted_findings", []))
        for row in predictions
    }
    prediction_by_id = {row["id"]: row for row in predictions}
    labels = sorted(
        {label for row in gold for label in row.get("expected_findings", [])}
        | {label for row in predictions for label in row.get("predicted_findings", [])}
    )
    report: dict[str, Any] = {}
    total_tp = total_fp = total_fn = 0
    wrong_cases = []
    exact_matches = 0
    for row in gold:
        expected = set(row.get("expected_findings", []))
        predicted = pred_by_id.get(row["id"], set())
        prediction = prediction_by_id.get(row["id"])
        failed = prediction is None or prediction.get("status", "completed") != "completed"
        if expected == predicted and not failed:
            exact_matches += 1
        if expected != predicted or failed:
            wrong_cases.append(
                {
                    "id": row["id"],
                    "expected": sorted(expected),
                    "actual": sorted(predicted),
                    "title": row.get("title", ""),
                    "failure": (
                        prediction.get("failure") if prediction and failed
                        else "Prediction is missing." if prediction is None
                        else None
                    ),
                }
            )
    for label in labels:
        tp = fp = fn = 0
        for row in gold:
            expected = set(row.get("expected_findings", []))
            predicted = pred_by_id.get(row["id"], set())
            tp += int(label in expected and label in predicted)
            fp += int(label not in expected and label in predicted)
            fn += int(label in expected and label not in predicted)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        report[label] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
        total_tp += tp
        total_fp += fp
        total_fn += fn

    error_findings = sum(int(row.get("error_findings", 0)) for row in predictions)
    failures = []
    for row in gold:
        prediction = prediction_by_id.get(row["id"])
        if prediction is None or prediction.get("status", "completed") != "completed":
            failures.append({
                "id": row["id"],
                "failure": (
                    prediction.get("failure") if prediction else None
                ) or ("Prediction is missing." if prediction is None else "Evaluation case failed."),
            })
    valid_source_errors = sum(
        int(row.get("valid_source_error_findings", 0)) for row in predictions
    )
    times = [
        float(row["elapsed_ms"])
        for row in predictions
        if isinstance(row.get("elapsed_ms"), (float, int))
    ]
    micro_precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    return {
        "examples": len(gold),
        "predictions_supplied": len(predictions),
        "coverage": round(len(predictions) / len(gold), 4) if gold else 0.0,
        "exact_match_accuracy": round(exact_matches / len(gold), 4) if gold else 0.0,
        "micro_precision": round(micro_precision, 4),
        "micro_recall": round(micro_recall, 4),
        "micro_f1": round(
            2 * micro_precision * micro_recall / (micro_precision + micro_recall), 4
        ) if micro_precision + micro_recall else 0.0,
        "false_flags": total_fp,
        "false_negatives": total_fn,
        "failed_cases": len(failures),
        "failures": failures,
        "error_findings": error_findings,
        "valid_source_error_findings": valid_source_errors,
        "share_error_findings_with_valid_source": round(
            valid_source_errors / error_findings, 4
        ) if error_findings else None,
        "needs_human_review_count": sum(
            int(row.get("needs_human_review_count", 0)) for row in predictions
        ),
        "median_check_time_ms": round(statistics.median(times), 2) if times else None,
        "slowest_check_time_ms": round(max(times), 2) if times else None,
        "by_label": report,
        "wrong_cases": wrong_cases,
        "note": (
            "Source validity is counted only when the recorded error finding cites a "
            "fact, approved fact, or active rule with a non-empty source_ref."
        ),
    }


def render_evaluation(
    gold: list[dict],
    variants: dict[str, list[dict]],
) -> str:
    if set(variants) != {"code_rules_only", "retrieval_and_nli", "full_pipeline"}:
        raise ValueError("Exactly the three named evaluation variants are required.")
    expected_ids = {row["id"] for row in gold}
    dataset_hashes = set()
    for name, rows in variants.items():
        ids = {row["id"] for row in rows}
        if ids != expected_ids:
            raise ValueError(
                f"{name} must contain exactly all {len(expected_ids)} gold case IDs."
            )
        if any(row.get("variant") != name for row in rows):
            raise ValueError(f"{name} predictions must identify their selected variant.")
        hashes = {row.get("dataset_sha256") for row in rows}
        if len(hashes) != 1 or None in hashes:
            raise ValueError(f"{name} predictions must share one dataset SHA-256.")
        dataset_hashes.update(hashes)
        if any(
            row.get("status", "completed") not in {"completed", "failed"}
            for row in rows
        ):
            raise ValueError(f"{name} predictions contain an invalid status.")
    if len(dataset_hashes) != 1:
        raise ValueError("All variants must use the same dataset SHA-256.")
    scored = {name: score(gold, rows) for name, rows in variants.items()}
    lines = [
        "# BrandCourt Evaluation",
        "",
        "Measured by `backend/scripts/evaluate_api.py` and `backend/scripts/score_eval.py`.",
        "These results are empirical for the recorded run and are not legal or policy advice.",
        "",
        "| Variant | Cases | Failures | Coverage | Exact-match accuracy | Micro precision | Micro recall | Micro F1 | False positives | False negatives | Valid-source error share | Needs human review | Median ms | Slowest ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, result in scored.items():
        lines.append(
            "| "
            + " | ".join(
                [
                    name.replace("_", " "),
                    str(result["predictions_supplied"]),
                    str(result["failed_cases"]),
                    f'{result["coverage"]:.1%}',
                    f'{result["exact_match_accuracy"]:.1%}',
                    f'{result["micro_precision"]:.1%}',
                    f'{result["micro_recall"]:.1%}',
                    f'{result["micro_f1"]:.1%}',
                    str(result["false_flags"]),
                    str(result["false_negatives"]),
                    (
                        f'{result["share_error_findings_with_valid_source"]:.1%}'
                        if result["share_error_findings_with_valid_source"] is not None
                        else "n/a"
                    ),
                    str(result["needs_human_review_count"]),
                    str(result["median_check_time_ms"]),
                    str(result["slowest_check_time_ms"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Precision and recall by finding type", ""])
    for name, result in scored.items():
        lines.extend(
            [
                f"### {name.replace('_', ' ').title()}",
                "",
                "| Finding type | TP | FP | FN | Precision | Recall | F1 |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for label, metrics in result["by_label"].items():
            lines.append(
                f'| {label} | {metrics["tp"]} | {metrics["fp"]} | {metrics["fn"]} '
                f'| {metrics["precision"]:.1%} | {metrics["recall"]:.1%} '
                f'| {metrics["f1"]:.1%} |'
            )
        lines.extend(["", "#### Cases scored incorrectly", ""])
        if result["wrong_cases"]:
            for case in result["wrong_cases"]:
                lines.append(
                    f'- `{case["id"]}` {case["title"]}: expected '
                    f'{case["expected"]}; observed {case["actual"]}.'
                )
        else:
            lines.append("- None.")
        if result["failures"]:
            lines.extend(["", "#### Failed cases", ""])
            lines.extend(
                f'- `{case["id"]}`: {case["failure"]}'
                for case in result["failures"]
            )
        lines.append("")
    lines.extend(
        [
            "## Reproducibility",
            "",
            f"All prediction files used the same dataset SHA-256: "
            f"`{next(iter(dataset_hashes))}`. Prediction rows identify their variant and record "
            "completed or failed jobs; failed jobs count as empty predictions, increasing false "
            "negatives rather than being silently omitted. Latency is measured from the durable "
            "worker's started_at to finished_at timestamps. The source-share definition is stated "
            "in each score output.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", default=str(DEFAULT_DATA))
    parser.add_argument("--predictions")
    parser.add_argument("--code-only")
    parser.add_argument("--retrieval-nli")
    parser.add_argument("--full")
    parser.add_argument("--evaluation-doc")
    parser.add_argument("--out")
    arguments = parser.parse_args()
    gold_rows = load(arguments.gold)
    variants = {
        "code_rules_only": arguments.code_only,
        "retrieval_and_nli": arguments.retrieval_nli,
        "full_pipeline": arguments.full,
    }
    if all(variants.values()):
        document = render_evaluation(
            gold_rows,
            {name: load(path) for name, path in variants.items()},
        )
        if not arguments.evaluation_doc:
            parser.error("--evaluation-doc is required when scoring all three variants.")
        Path(arguments.evaluation_doc).write_text(document, encoding="utf-8")
        print(document)
    elif arguments.predictions:
        result = score(gold_rows, load(arguments.predictions))
        output = json.dumps(result, indent=2)
        if arguments.out:
            Path(arguments.out).write_text(output + "\n", encoding="utf-8")
        print(output)
    else:
        parser.error(
            "Provide --predictions or all three of --code-only, --retrieval-nli, and --full."
        )
