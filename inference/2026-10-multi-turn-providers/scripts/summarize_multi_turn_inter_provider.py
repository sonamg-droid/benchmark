#!/usr/bin/env python3
"""Summarize the inter-provider multi-turn benchmark without a composite score."""

from __future__ import annotations

import argparse
import csv
import html
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
MODEL_ORDER = ("GLM 5.3 Flash", "GLM 5.3", "Kimi K3")
PROVIDER_ORDER = ("Telnyx", "Baseten", "Together AI", "Fireworks")


def percentile(values: Iterable[float], p: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    rank = (len(ordered) - 1) * p
    low, high = math.floor(rank), math.ceil(rank)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def family(conversation: dict[str, Any]) -> str:
    label = conversation["model_label"]
    return label.split(" - ", 1)[1] if " - " in label else label


def cell_key(conversation: dict[str, Any]) -> tuple[str, str]:
    return family(conversation), conversation.get("provider_label", conversation.get("provider", "unknown"))


def rate(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else 100 * numerator / denominator


def fmt_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}%"


def fmt_num(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def fmt_seconds(value: float | None) -> str:
    return "N/A" if value is None else f"{value / 1000:.2f}s"


def sort_key(row: dict[str, Any]) -> tuple[int, int]:
    return MODEL_ORDER.index(row["model_family"]), PROVIDER_ORDER.index(row["provider"])


def is_model_leader(cells: list[dict[str, Any]], row: dict[str, Any], field: str, direction: str) -> bool:
    eligible = [
        candidate[field]
        for candidate in cells
        if candidate["model_family"] == row["model_family"] and candidate.get(field) is not None
    ]
    if not eligible or row.get(field) is None:
        return False
    best = max(eligible) if direction == "high" else min(eligible)
    return abs(row[field] - best) < 1e-9


def mark_telnyx(value: str, cells: list[dict[str, Any]], row: dict[str, Any], field: str, direction: str) -> str:
    if row["provider"] == "Telnyx" and is_model_leader(cells, row, field, direction):
        return f"{value}*"
    return value


def summarize(conversations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for conversation in conversations:
        grouped[cell_key(conversation)].append(conversation)

    cells: list[dict[str, Any]] = []
    judge_detail: list[dict[str, Any]] = []
    for (model_family, provider), items in grouped.items():
        completed = [item for item in items if item.get("ok")]
        turns = [turn for item in completed for turn in item.get("turns", []) if turn.get("ok")]
        checks = [check for item in completed for check in item.get("objective_checks", [])]
        judges = [judge for item in completed for judge in item.get("judges", []) if judge.get("ok") and judge.get("scores")]
        judge_votes = [judge for judge in judges if judge.get("completed") is True]
        scores = [score for judge in judges for score in judge["scores"].values()]
        total_times = [item["total_response_ms"] for item in completed if item.get("total_response_ms") is not None]

        row: dict[str, Any] = {
            "model_family": model_family,
            "provider": provider,
            "conversation_attempts": len(items),
            "completed_conversations": len(completed),
            "conversation_success_rate": rate(len(completed), len(items)),
            "successful_turns": len(turns),
            "expected_turns": sum(item.get("expected_turns", 0) for item in items),
            "request_failure_rate": rate(sum(item.get("request_failures", 0) for item in items), sum(item.get("expected_turns", 0) for item in items)),
            "objective_checks_passed": sum(bool(check.get("passed")) for check in checks),
            "objective_checks_total": len(checks),
            "objective_check_rate": rate(sum(bool(check.get("passed")) for check in checks), len(checks)),
            "judge_completion_votes": len(judge_votes),
            "judge_results": len(judges),
            "judge_completion_rate": rate(len(judge_votes), len(judges)),
            "mean_blind_quality_score": mean(scores) if scores else None,
            "p50_total_response_ms": percentile(total_times, 0.50),
            "p95_total_response_ms": percentile(total_times, 0.95),
            "mean_input_tokens": mean(item["input_tokens"] for item in completed if item.get("input_tokens") is not None) if any(item.get("input_tokens") is not None for item in completed) else None,
            "mean_output_tokens": mean(item["output_tokens"] for item in completed if item.get("output_tokens") is not None) if any(item.get("output_tokens") is not None for item in completed) else None,
            "mean_total_tokens": mean(item["total_tokens"] for item in completed if item.get("total_tokens") is not None) if any(item.get("total_tokens") is not None for item in completed) else None,
        }
        for metric in ("ttft_ms", "ttfa_ms", "e2e_ms"):
            values = [turn[metric] for turn in turns if turn.get(metric) is not None]
            row[f"p50_{metric}"] = percentile(values, 0.50)
            row[f"p95_{metric}"] = percentile(values, 0.95)
        cells.append(row)

        by_judge: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for judge in judges:
            by_judge[judge["judge_label"]].append(judge)
        for judge_label, evaluations in by_judge.items():
            detail: dict[str, Any] = {
                "model_family": model_family,
                "provider": provider,
                "judge": judge_label,
                "evaluations": len(evaluations),
                "completion_rate": rate(sum(item.get("completed") is True for item in evaluations), len(evaluations)),
            }
            for field in SCORE_FIELDS:
                detail[field] = mean(item["scores"][field] for item in evaluations)
            judge_detail.append(detail)

    cells.sort(key=sort_key)
    judge_detail.sort(key=lambda row: (*sort_key(row), row["judge"]))
    return cells, judge_detail


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def winners(cells: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    categories = (
        ("Blind quality", "mean_blind_quality_score", "high"),
        ("Judge completion", "judge_completion_rate", "high"),
        ("Objective checks", "objective_check_rate", "high"),
        ("Reliability", "conversation_success_rate", "high"),
        ("Median total response time", "p50_total_response_ms", "low"),
        ("Observed p95 total response time", "p95_total_response_ms", "low"),
        ("Median time to first answer", "p50_ttfa_ms", "low"),
        ("Median per-turn E2E", "p50_e2e_ms", "low"),
    )
    for model in MODEL_ORDER:
        candidates = [row for row in cells if row["model_family"] == model and row.get("conversation_attempts")]
        for category, field, direction in categories:
            eligible = [row for row in candidates if row.get(field) is not None]
            if not eligible:
                continue
            best_value = (max if direction == "high" else min)(row[field] for row in eligible)
            providers = [row["provider"] for row in eligible if abs(row[field] - best_value) < 1e-9]
            if field.endswith("_ms"):
                value = fmt_seconds(best_value)
            elif "rate" in field:
                value = fmt_pct(best_value)
            else:
                value = fmt_num(best_value)
            rows.append({"model_family": model, "category": category, "winner": ", ".join(providers), "value": value})
    return rows


def failure_rows(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for conversation in conversations:
        grouped[cell_key(conversation)].append(conversation)
    rows: list[dict[str, Any]] = []
    for (model_family, provider), items in grouped.items():
        failures = [item for item in items if not item.get("ok")]
        if not failures:
            continue
        statuses: dict[str, int] = defaultdict(int)
        for item in failures:
            for turn in item.get("turns", []):
                if turn.get("ok"):
                    continue
                status = turn.get("status")
                error = str(turn.get("error") or "")
                if status == 429:
                    label = "HTTP 429 rate limit"
                elif status == 503:
                    label = "HTTP 503 provider error"
                elif status == 500:
                    label = "HTTP 500 provider error"
                elif "No visible answer content" in error:
                    label = "No visible answer content"
                else:
                    label = f"Status {status or 'unknown'} stream error"
                statuses[label] += 1
        rows.append(
            {
                "model_family": model_family,
                "provider": provider,
                "failed_conversations": len(failures),
                "attempts": len(items),
                "failure_rate": rate(len(failures), len(items)),
                "failure_types": "; ".join(f"{label}: {count}" for label, count in sorted(statuses.items())),
            }
        )
    rows.sort(key=sort_key)
    return rows


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_markdown(
    state: dict[str, Any],
    cells: list[dict[str, Any]],
    winner_rows: list[dict[str, str]],
    failures: list[dict[str, Any]],
) -> str:
    keyed = {(row["model_family"], row["provider"]): row for row in cells}
    telnyx_leaders = defaultdict(list)
    for leader in winner_rows:
        if "Telnyx" in leader["winner"].split(", "):
            telnyx_leaders[leader["model_family"]].append(leader["category"])
    failure_totals = defaultdict(int)
    for failure in failures:
        failure_totals[failure["provider"]] += failure["failed_conversations"]
    quality_values = [row["mean_blind_quality_score"] for row in cells if row.get("mean_blind_quality_score") is not None]
    interpretation = []
    for model in MODEL_ORDER:
        categories = telnyx_leaders.get(model, [])
        if categories:
            interpretation.append(f"- **Telnyx led or tied for {model} in:** {', '.join(categories)}.")
    for model in MODEL_ORDER:
        telnyx = keyed[(model, "Telnyx")]
        fastest = min(
            (row for row in cells if row["model_family"] == model),
            key=lambda row: row["p50_total_response_ms"],
        )
        if telnyx["p50_total_response_ms"] > fastest["p50_total_response_ms"] * 1.5:
            interpretation.append(
                f"- **Telnyx {model} median conversation latency is worth investigating:** "
                f"{fmt_seconds(telnyx['p50_total_response_ms'])} versus "
                f"{fmt_seconds(fastest['p50_total_response_ms'])} for {fastest['provider']}."
            )
    if failure_totals:
        failure_text = ", ".join(f"{provider}: {count}" for provider, count in sorted(failure_totals.items(), key=lambda item: (-item[1], item[0])))
        interpretation.append(f"- **Observed failed conversations:** {failure_text}.")
    if quality_values:
        interpretation.append(
            f"- **Blind quality scores ranged from {min(quality_values):.2f} to {max(quality_values):.2f} and came from one judge.** "
            "Treat small differences as directional rather than decisive."
        )
    interpretation.append("- **There is no weighted overall winner.** Quality, completion, reliability, and latency should be read separately.")
    lines = [
        "# Inter-provider multi-turn task completion benchmark",
        "",
        "This report compares the same three model families across Telnyx, Baseten, Together AI, and Fireworks. Quality, completion, reliability, and latency are reported separately; there is no weighted overall score.",
        "",
        "## Interpretation",
        "",
        *interpretation,
        "",
        "## Summary table",
        "",
        md_table(
            ["Model", "Provider", "Successful conversations", "Blind quality /5", "Judge completion", "Objective checks", "p50 conversation latency", "p95 conversation latency", "p50 TTFT latency", "p50 TTFA latency"],
            [[
                row["model_family"], row["provider"],
                mark_telnyx(f"{row['completed_conversations']}/{row['conversation_attempts']}", cells, row, "conversation_success_rate", "high"),
                mark_telnyx(f"{fmt_num(row['mean_blind_quality_score'])} (n={row['judge_results']})", cells, row, "mean_blind_quality_score", "high"),
                mark_telnyx(fmt_pct(row["judge_completion_rate"]), cells, row, "judge_completion_rate", "high"),
                mark_telnyx(fmt_pct(row["objective_check_rate"]), cells, row, "objective_check_rate", "high"),
                mark_telnyx(fmt_seconds(row["p50_total_response_ms"]), cells, row, "p50_total_response_ms", "low"),
                mark_telnyx(fmt_seconds(row["p95_total_response_ms"]), cells, row, "p95_total_response_ms", "low"),
                mark_telnyx(fmt_seconds(row["p50_ttft_ms"]), cells, row, "p50_ttft_ms", "low"),
                mark_telnyx(fmt_seconds(row["p50_ttfa_ms"]), cells, row, "p50_ttfa_ms", "low"),
            ] for row in cells],
        ),
        "",
        "\\* Telnyx led or tied for the lead within that model family.",
        "",
        "Conversation latency is the total model response time across all turns in the fixed multi-turn conversation. It sums per-turn E2E model response time and excludes user pauses. TTFT is time to first model activity; TTFA is time to first visible answer content. Latency percentiles include successful conversations only.",
        "",
        "## Token usage per completed conversation",
        "",
        md_table(
            ["Model", "Provider", "Mean input tokens", "Mean output tokens", "Mean total tokens"],
            [[
                row["model_family"], row["provider"], fmt_num(row["mean_input_tokens"], 0),
                fmt_num(row["mean_output_tokens"], 0), fmt_num(row["mean_total_tokens"], 0),
            ] for row in cells],
        ),
        "",
        "## Per-turn latency",
        "",
        md_table(
            ["Model", "Provider", "Turns", "p50 TTFT", "p50 TTFA", "p95 TTFA", "p50 E2E", "p95 E2E"],
            [[
                row["model_family"], row["provider"], str(row["successful_turns"]),
                fmt_seconds(row["p50_ttft_ms"]), fmt_seconds(row["p50_ttfa_ms"]),
                fmt_seconds(row["p95_ttfa_ms"]), fmt_seconds(row["p50_e2e_ms"]),
                fmt_seconds(row["p95_e2e_ms"]),
            ] for row in cells],
        ),
        "",
        "## Category leaders",
        "",
        md_table(
            ["Model", "Category", "Provider", "Result"],
            [[row["model_family"], row["category"], row["winner"], row["value"]] for row in winner_rows],
        ),
        "",
        "## Failure breakdown",
        "",
        md_table(
            ["Model", "Provider", "Failed", "Failure rate", "Observed causes"],
            [[
                row["model_family"], row["provider"],
                f"{row['failed_conversations']}/{row['attempts']}", fmt_pct(row["failure_rate"]),
                row["failure_types"],
            ] for row in failures],
        ),
        "",
        "## Methodology",
        "",
        f"- Dataset: `{state.get('datasetVersion', 'unknown')}` with 15 fixed multi-turn scenarios.",
        "- Each provider/model cell ran each scenario three times. Blind judging was performed on successful repeat-1 conversations by DeepSeek V4.1 Flash; deterministic checks and latency were collected on all successful repeats.",
        "- All requests originated from the same Telnyx stateful actor and called each provider's public API.",
        "- Conversation history contained visible assistant answers only. Hidden reasoning was captured for audit but was not added to later turns.",
        "- `reasoning_effort` was requested as `low` for every candidate. Provider implementations may still differ.",
        "- TTFT is the first non-empty model delta. TTFA is the first non-whitespace visible answer content. E2E ends when the streamed model response completes.",
        "- Failed requests remain reliability failures and are excluded from successful-request latency percentiles. Judge failures are not converted into low candidate scores.",
        "- Observed p95 values describe this sample and are not provider SLAs.",
        "",
    ]
    return "\n".join(lines)


def build_html(cells: list[dict[str, Any]], winner_rows: list[dict[str, str]], failures: list[dict[str, Any]]) -> str:
    def table(headers: list[str], rows: list[list[str]]) -> str:
        head = "".join(f"<th>{html.escape(value)}</th>" for value in headers)
        body = "".join("<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>" for row in rows)
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    summary = table(
        ["Model", "Provider", "Successful conversations", "Blind quality /5", "Judge completion", "Objective checks", "p50 conversation latency", "p95 conversation latency", "p50 TTFT latency", "p50 TTFA latency"],
        [[
            row["model_family"], row["provider"],
            mark_telnyx(f"{row['completed_conversations']}/{row['conversation_attempts']}", cells, row, "conversation_success_rate", "high"),
            mark_telnyx(f"{fmt_num(row['mean_blind_quality_score'])} (n={row['judge_results']})", cells, row, "mean_blind_quality_score", "high"),
            mark_telnyx(fmt_pct(row["judge_completion_rate"]), cells, row, "judge_completion_rate", "high"),
            mark_telnyx(fmt_pct(row["objective_check_rate"]), cells, row, "objective_check_rate", "high"),
            mark_telnyx(fmt_seconds(row["p50_total_response_ms"]), cells, row, "p50_total_response_ms", "low"),
            mark_telnyx(fmt_seconds(row["p95_total_response_ms"]), cells, row, "p95_total_response_ms", "low"),
            mark_telnyx(fmt_seconds(row["p50_ttft_ms"]), cells, row, "p50_ttft_ms", "low"),
            mark_telnyx(fmt_seconds(row["p50_ttfa_ms"]), cells, row, "p50_ttfa_ms", "low"),
        ] for row in cells],
    )
    leaders = table(["Model", "Category", "Provider", "Result"], [[row["model_family"], row["category"], row["winner"], row["value"]] for row in winner_rows])
    failure_table = table(["Model", "Provider", "Failed", "Failure rate", "Observed causes"], [[row["model_family"], row["provider"], f"{row['failed_conversations']}/{row['attempts']}", fmt_pct(row["failure_rate"]), row["failure_types"]] for row in failures])
    return f"""<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Inter-provider multi-turn benchmark</title><style>body{{font-family:Arial,sans-serif;background:#080808;color:#fefdf5;margin:0;padding:48px}}main{{max-width:1700px;margin:auto}}h1,h2{{letter-spacing:0}}p,li{{color:#c9c7bf;line-height:1.55}}table{{width:100%;border-collapse:collapse;margin:20px 0 16px;font-size:14px}}th,td{{padding:12px;border-bottom:1px solid #3a3a36;text-align:left;vertical-align:top}}th{{color:#00e3aa}}.note{{border-left:4px solid #00e3aa;padding-left:16px}}.table-note{{margin:0 0 44px}}</style></head><body><main><h1>Inter-provider multi-turn task completion benchmark</h1><p class=\"note\">Quality, completion, reliability, and latency are reported separately. There is no weighted overall score.</p><h2>Summary table</h2>{summary}<p class=\"table-note\">* Telnyx led or tied for the lead within that model family. Conversation latency is total model response time across every turn in the fixed multi-turn conversation. It excludes user pauses. TTFT is time to first model activity; TTFA is time to first visible answer content. Latency percentiles include successful conversations only.</p><h2>Category leaders</h2>{leaders}<h2>Failure breakdown</h2>{failure_table}<h2>Measurement notes</h2><ul><li>All requests originated from the same Telnyx stateful actor and called each provider's public API.</li><li>Observed p95 values describe this sample and are not provider SLAs.</li></ul></main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    payload = json.loads((args.run_directory / "results.json").read_text(encoding="utf-8"))
    state = payload.get("state") or {}
    conversations = payload.get("conversations") or []
    cells, judge_detail = summarize(conversations)
    winner_rows = winners(cells)
    failures = failure_rows(conversations)
    write_csv(args.run_directory / "provider_model_summary.csv", cells)
    write_csv(args.run_directory / "quality_by_provider_model_judge.csv", judge_detail)
    write_csv(args.run_directory / "category_leaders.csv", winner_rows)
    write_csv(args.run_directory / "failure_summary.csv", failures)
    (args.run_directory / "report.md").write_text(build_markdown(state, cells, winner_rows, failures), encoding="utf-8")
    (args.run_directory / "report.html").write_text(build_html(cells, winner_rows, failures), encoding="utf-8")
    print(f"Wrote summaries to {args.run_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
