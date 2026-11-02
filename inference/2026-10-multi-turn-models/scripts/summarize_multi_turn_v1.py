#!/usr/bin/env python3
"""Create audit-friendly summaries for a completed multi-turn v1 run."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


SCORE_FIELDS = (
    "task_completion",
    "correctness",
    "state_tracking",
    "correction_following",
    "final_answer_usability",
)


def percentile(values: Iterable[float], p: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    rank = (len(ordered) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def fmt_number(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def fmt_seconds(value_ms: float | None) -> str:
    return "N/A" if value_ms is None else f"{value_ms / 1000:.2f}s"


def pct(numerator: int, denominator: int) -> str:
    return "N/A" if denominator == 0 else f"{100 * numerator / denominator:.1f}%"


def load_results(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("conversations"), list):
        raise ValueError("results.json must contain a conversations array")
    return payload.get("state") or {}, payload["conversations"]


def model_rows(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for conversation in conversations:
        grouped[conversation["model_label"]].append(conversation)

    rows: list[dict[str, Any]] = []
    for model, items in sorted(grouped.items()):
        completed = [item for item in items if item.get("ok")]
        checks = [check for item in completed for check in item.get("objective_checks", [])]
        judges = [judge for item in completed for judge in item.get("judges", []) if judge.get("ok")]
        completion_votes = [judge for judge in judges if judge.get("completed") is True]
        times = [item["total_response_ms"] for item in completed if item.get("total_response_ms") is not None]
        input_tokens = [item["input_tokens"] for item in completed if item.get("input_tokens") is not None]
        output_tokens = [item["output_tokens"] for item in completed if item.get("output_tokens") is not None]
        rows.append(
            {
                "model": model,
                "conversations": len(items),
                "completed_conversations": len(completed),
                "request_completion_rate": pct(len(completed), len(items)),
                "objective_checks_passed": sum(bool(check.get("passed")) for check in checks),
                "objective_checks_total": len(checks),
                "objective_check_rate": pct(sum(bool(check.get("passed")) for check in checks), len(checks)),
                "judge_completion_votes": len(completion_votes),
                "judge_results": len(judges),
                "judge_completion_rate": pct(len(completion_votes), len(judges)),
                "p50_total_response_ms": percentile(times, 0.5),
                "p95_total_response_ms": percentile(times, 0.95),
                "mean_input_tokens": mean(input_tokens) if input_tokens else None,
                "mean_output_tokens": mean(output_tokens) if output_tokens else None,
            }
        )
    return rows


def latency_rows(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for conversation in conversations:
        for turn in conversation.get("turns", []):
            if turn.get("ok"):
                grouped[conversation["model_label"]].append(turn)

    rows: list[dict[str, Any]] = []
    for model, turns in sorted(grouped.items()):
        row: dict[str, Any] = {"model": model, "successful_turns": len(turns)}
        for metric in ("ttft_ms", "ttfa_ms", "e2e_ms"):
            values = [turn[metric] for turn in turns if turn.get(metric) is not None]
            row[f"p50_{metric}"] = percentile(values, 0.5)
            row[f"p95_{metric}"] = percentile(values, 0.95)
        rows.append(row)
    return rows


def quality_rows(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for conversation in conversations:
        for judge in conversation.get("judges", []):
            if judge.get("ok") and isinstance(judge.get("scores"), dict):
                grouped[(conversation["model_label"], judge["judge_label"])].append(judge)

    rows: list[dict[str, Any]] = []
    for (model, judge), evaluations in sorted(grouped.items()):
        row: dict[str, Any] = {"model": model, "judge": judge, "evaluations": len(evaluations)}
        for field in SCORE_FIELDS:
            row[field] = mean(item["scores"][field] for item in evaluations)
        rows.append(row)
    return rows


def agreement_rows(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for conversation in conversations:
        judges = [judge for judge in conversation.get("judges", []) if judge.get("ok")]
        if len(judges) != 2:
            continue
        scores_a = judges[0]["scores"]
        scores_b = judges[1]["scores"]
        rows.append(
            {
                "model": conversation["model_label"],
                "scenario_id": conversation["scenario_id"],
                "completion_agreement": judges[0]["completed"] == judges[1]["completed"],
                "mean_absolute_score_difference": mean(
                    abs(scores_a[field] - scores_b[field]) for field in SCORE_FIELDS
                ),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_report(
    state: dict[str, Any],
    conversations: list[dict[str, Any]],
    models: list[dict[str, Any]],
    latencies: list[dict[str, Any]],
    qualities: list[dict[str, Any]],
    agreements: list[dict[str, Any]],
) -> str:
    lines = [
        "# Multi-turn task completion benchmark v1",
        "",
        "This report keeps completion, quality, reliability, latency, and token usage separate. It does not calculate a composite winner.",
        "",
        "## Run scope",
        "",
        f"- Dataset: `{state.get('datasetVersion', 'unknown')}`",
        f"- Candidate models: {len(state.get('models', []))}",
        f"- Scenarios: {len(state.get('scenarios', []))}",
        f"- Conversation attempts: {len(conversations)}",
        f"- Blind judges: {', '.join(judge.get('label', judge.get('id', 'unknown')) for judge in state.get('judges', []))}",
        "",
        "## Completion, reliability, and tokens",
        "",
        markdown_table(
            ["Model", "Completed", "Objective checks", "Judge completion", "Mean input tokens", "Mean output tokens"],
            [
                [
                    row["model"],
                    f"{row['completed_conversations']}/{row['conversations']} ({row['request_completion_rate']})",
                    f"{row['objective_checks_passed']}/{row['objective_checks_total']} ({row['objective_check_rate']})",
                    f"{row['judge_completion_votes']}/{row['judge_results']} ({row['judge_completion_rate']})",
                    fmt_number(row["mean_input_tokens"], 0),
                    fmt_number(row["mean_output_tokens"], 0),
                ]
                for row in models
            ],
        ),
        "",
        "## Blind quality scores",
        "",
        "Scores use a 1-5 rubric. Results are shown per judge rather than silently averaged across judges.",
        "",
        markdown_table(
            ["Model", "Judge", "N", "Task completion", "Correctness", "State tracking", "Corrections", "Usability"],
            [
                [
                    row["model"], row["judge"], str(row["evaluations"]),
                    fmt_number(row["task_completion"]), fmt_number(row["correctness"]),
                    fmt_number(row["state_tracking"]), fmt_number(row["correction_following"]),
                    fmt_number(row["final_answer_usability"]),
                ]
                for row in qualities
            ],
        ),
        "",
        "## Per-turn latency",
        "",
        markdown_table(
            ["Model", "Successful turns", "p50 TTFT", "p95 TTFT", "p50 TTFA", "p95 TTFA", "p50 E2E", "p95 E2E"],
            [
                [
                    row["model"], str(row["successful_turns"]),
                    fmt_seconds(row["p50_ttft_ms"]), fmt_seconds(row["p95_ttft_ms"]),
                    fmt_seconds(row["p50_ttfa_ms"]), fmt_seconds(row["p95_ttfa_ms"]),
                    fmt_seconds(row["p50_e2e_ms"]), fmt_seconds(row["p95_e2e_ms"]),
                ]
                for row in latencies
            ],
        ),
        "",
        "## Total conversation response time",
        "",
        markdown_table(
            ["Model", "p50 total response time", "p95 total response time"],
            [[row["model"], fmt_seconds(row["p50_total_response_ms"]), fmt_seconds(row["p95_total_response_ms"])] for row in models],
        ),
        "",
        "## Judge agreement",
        "",
    ]
    if agreements:
        completion_agreement = sum(bool(row["completion_agreement"]) for row in agreements)
        mean_difference = mean(row["mean_absolute_score_difference"] for row in agreements)
        lines.extend(
            [
                f"- Completion decision agreement: {completion_agreement}/{len(agreements)} ({pct(completion_agreement, len(agreements))})",
                f"- Mean absolute difference across the five rubric scores: {mean_difference:.2f} points",
                "- Review individual conversations when the judges disagree on completion or differ materially on scores.",
            ]
        )
    else:
        lines.append("No conversations had two successfully parsed judge results.")
    lines.extend(
        [
            "",
            "## Measurement notes",
            "",
            "- TTFT is the first non-empty model delta and may be reasoning.",
            "- TTFA is the first non-whitespace visible answer content.",
            "- E2E is measured per model turn. Total response time is the sum of successful model-turn E2E values within a conversation.",
            "- Failed model requests are counted as reliability failures and excluded from successful-turn latency percentiles.",
            "- Judge failures remain visible and are not converted into low candidate scores.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    results_path = args.run_directory / "results.json"
    state, conversations = load_results(results_path)
    models = model_rows(conversations)
    latencies = latency_rows(conversations)
    qualities = quality_rows(conversations)
    agreements = agreement_rows(conversations)

    write_csv(args.run_directory / "model_summary.csv", models)
    write_csv(args.run_directory / "latency_summary.csv", latencies)
    write_csv(args.run_directory / "quality_by_judge.csv", qualities)
    write_csv(args.run_directory / "judge_agreement.csv", agreements)
    report = build_report(state, conversations, models, latencies, qualities, agreements)
    (args.run_directory / "report.md").write_text(report, encoding="utf-8")
    print(f"Wrote summaries to {args.run_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
