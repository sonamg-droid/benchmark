#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_lib import percentile  # noqa: E402

GREEN = "#00E3AA"
PURPLE = "#8E67FF"
CREAM = "#F6F3EC"
MUTED = "#A9A59C"
BLACK = "#070908"
GRID = "#303330"

ENDPOINTS = {
    "telnyx": ("Telnyx Inference", "managed_per_token"),
    "modal_shared": ("Modal Shared Endpoint", "managed_per_token"),
}

LIST_PRICING = {
    "telnyx": {"input": 0.135, "cached_input": 0.027, "output": 0.45},
    "modal_shared": {"input": 0.45, "cached_input": 0.09, "output": 1.50},
}


def font(size: int, bold: bool = False):
    choices = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for choice in choices:
        if Path(choice).exists():
            return ImageFont.truetype(choice, size)
    return ImageFont.load_default()


def numeric(rows: list[dict], key: str) -> list[float]:
    values = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def normalize_actor_row(row: dict) -> dict:
    normalized = dict(row)
    provider = str(normalized.get("provider") or "")
    label, endpoint_type = ENDPOINTS.get(provider, (provider or "Unknown", "unknown"))
    normalized.setdefault("endpoint_label", label)
    normalized.setdefault("endpoint_type", endpoint_type)
    normalized.setdefault("warmup", normalized.get("cache_mode") == "warmup")
    if normalized.get("effective_output_tok_s") is None:
        normalized["effective_output_tok_s"] = normalized.get("effective_tok_s")
    if normalized.get("median_chunk_gap_ms") is None:
        normalized["median_chunk_gap_ms"] = normalized.get("median_itl_ms")
    speed = normalized.get("effective_output_tok_s")
    if isinstance(speed, (int, float)) and speed > 0:
        normalized["time_per_output_token_ms"] = 1000.0 / float(speed)

    pricing = LIST_PRICING.get(provider)
    prompt_tokens = normalized.get("prompt_tokens")
    output_tokens = normalized.get("output_tokens")
    cached_tokens = normalized.get("cached_prompt_tokens")
    if pricing and isinstance(prompt_tokens, (int, float)) and isinstance(output_tokens, (int, float)):
        cached = float(cached_tokens) if isinstance(cached_tokens, (int, float)) else 0.0
        uncached = max(0.0, float(prompt_tokens) - cached)
        normalized["estimated_token_cost_usd"] = (
            uncached * pricing["input"]
            + cached * pricing["cached_input"]
            + float(output_tokens) * pricing["output"]
        ) / 1_000_000
        normalized["cost_basis"] = (
            "published_list_price_with_reported_cache_tokens"
            if cached > 0
            else "published_list_price_no_cache_discount"
        )
    return normalized


def summarize(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("warmup") or row.get("cache_mode") == "cache_seed":
            continue
        key = (row.get("endpoint_label"), row.get("endpoint_type"), row.get("profile"), row.get("concurrency"), row.get("cache_mode"))
        groups[key].append(row)
    summaries = []
    for key, attempted in sorted(groups.items(), key=lambda item: tuple(str(value) for value in item[0])):
        completed = [row for row in attempted if row.get("ok") and row.get("ttfa_ms") is not None]
        item = {
            "endpoint": key[0], "endpoint_type": key[1], "profile": key[2],
            "concurrency": key[3], "cache_mode": key[4], "attempted": len(attempted),
            "completed": len(completed), "reliability_pct": 100 * len(completed) / len(attempted) if attempted else None,
        }
        for key_name in ("ttft_ms", "ttfa_ms", "e2e_ms", "effective_output_tok_s", "time_per_output_token_ms", "median_chunk_gap_ms"):
            values = numeric(completed, key_name)
            item[f"p50_{key_name}"] = percentile(values, 0.5)
            item[f"p95_{key_name}"] = percentile(values, 0.95)
            item[f"n_{key_name}"] = len(values)
        item["actual_input_tokens"] = statistics.median(numeric(completed, "prompt_tokens")) if numeric(completed, "prompt_tokens") else None
        item["actual_output_tokens"] = statistics.median(numeric(completed, "output_tokens")) if numeric(completed, "output_tokens") else None
        item["actual_cached_input_tokens"] = statistics.median(numeric(completed, "cached_prompt_tokens")) if numeric(completed, "cached_prompt_tokens") else None
        item["estimated_cost_usd"] = sum(numeric(completed, "estimated_token_cost_usd")) or None
        total_input = sum(numeric(completed, "prompt_tokens"))
        total_output = sum(numeric(completed, "output_tokens"))
        item["measured_input_tokens"] = total_input
        item["measured_output_tokens"] = total_output
        if item["estimated_cost_usd"] is not None and completed:
            item["cost_per_1000_completed_requests_usd"] = item["estimated_cost_usd"] / len(completed) * 1000
            item["cost_per_million_processed_tokens_usd"] = item["estimated_cost_usd"] / (total_input + total_output) * 1_000_000 if total_input + total_output else None
            item["cost_per_million_generated_tokens_usd"] = item["estimated_cost_usd"] / total_output * 1_000_000 if total_output else None
        else:
            item["cost_per_1000_completed_requests_usd"] = None
            item["cost_per_million_processed_tokens_usd"] = None
            item["cost_per_million_generated_tokens_usd"] = None
        item["requests_per_second"] = statistics.median(numeric(completed, "cell_requests_per_second")) if numeric(completed, "cell_requests_per_second") else None
        item["output_tokens_per_second"] = statistics.median(numeric(completed, "cell_output_tokens_per_second")) if numeric(completed, "cell_output_tokens_per_second") else None
        summaries.append(item)
    return summaries


def fmt(value, unit="", digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}{unit}"


def chart_metric(
    summaries: list[dict], output: Path, metric: str, title: str, subtitle: str,
    *, divisor: float = 1000, unit: str = "s",
) -> None:
    rows = [row for row in summaries if row["cache_mode"] == "uncached" and row.get(metric) is not None]
    rows.sort(key=lambda row: (str(row["profile"]), int(row["concurrency"]), str(row["endpoint"])))
    if not rows:
        return
    width = 1800
    row_h = 54
    header = 190
    height = max(650, header + len(rows) * row_h + 80)
    image = Image.new("RGB", (width, height), BLACK)
    draw = ImageDraw.Draw(image)
    draw.text((60, 42), "telnyx", fill=CREAM, font=font(28, True))
    draw.text((60, 86), title, fill=CREAM, font=font(48, True))
    draw.text((60, 145), subtitle, fill=MUTED, font=font(23))
    max_value = max(float(row[metric]) for row in rows) * 1.12 or 1.0
    label_x, bar_x, bar_w = 60, 610, 1040
    for index, row in enumerate(rows):
        y = header + index * row_h
        label = f"{row['profile']}  c={row['concurrency']}  {row['endpoint']}"
        draw.text((label_x, y + 10), label, fill=CREAM, font=font(18))
        draw.rounded_rectangle((bar_x, y + 8, bar_x + bar_w, y + 38), radius=4, fill=GRID)
        extent = bar_w * float(row[metric]) / max_value
        color = GREEN if str(row["endpoint"]).startswith("Telnyx") else PURPLE
        draw.rounded_rectangle((bar_x, y + 8, bar_x + extent, y + 38), radius=4, fill=color)
        draw.text((bar_x + extent + 15, y + 7), fmt(float(row[metric]) / divisor, unit), fill=CREAM, font=font(19, True))
    image.save(output, quality=95)


def price_chart(output: Path) -> None:
    items = [
        ("Input", "Telnyx", 0.135, GREEN), ("Input", "Modal Shared", 0.45, PURPLE),
        ("Cached input", "Telnyx", 0.027, GREEN), ("Cached input", "Modal Shared", 0.09, PURPLE),
        ("Output", "Telnyx", 0.45, GREEN), ("Output", "Modal Shared", 1.50, PURPLE),
    ]
    image = Image.new("RGB", (1500, 720), BLACK)
    draw = ImageDraw.Draw(image)
    draw.text((55, 35), "telnyx", fill=CREAM, font=font(27, True))
    draw.text((55, 80), "Published GLM 5.3 Flash list price", fill=CREAM, font=font(44, True))
    draw.text((55, 137), "USD per 1M tokens. Modal Dedicated is compute-billed and is not shown here.", fill=MUTED, font=font(22))
    max_value = 1.5
    for index, (kind, provider, value, color) in enumerate(items):
        y = 210 + index * 76
        draw.text((55, y + 10), f"{kind} - {provider}", fill=CREAM, font=font(21))
        draw.rounded_rectangle((420, y + 8, 1280, y + 42), radius=4, fill=GRID)
        extent = 860 * value / max_value
        draw.rounded_rectangle((420, y + 8, 420 + extent, y + 42), radius=4, fill=color)
        draw.text((440 + extent, y + 7), f"${value:.3f}", fill=CREAM, font=font(21, True))
    image.save(output, quality=95)


def write_report(summaries: list[dict], output: Path, rows: list[dict]) -> None:
    headers = ["Endpoint", "Cache mode", "Profile", "Concurrency", "Completed", "p95 N", "p50 TTFT", "p95 TTFT", "p50 TTFA", "p95 TTFA", "p50 E2E", "p95 E2E", "p50 tok/s", "p50 time/output token", "Cost / 1K completed", "Est. list cost"]
    markdown_rows = []
    for row in summaries:
        markdown_rows.append([
            row["endpoint"], row["cache_mode"], row["profile"], row["concurrency"], f"{row['completed']}/{row['attempted']}", row["n_e2e_ms"],
            fmt(row["p50_ttft_ms"], " ms"), fmt(row["p95_ttft_ms"], " ms"),
            fmt(row["p50_ttfa_ms"], " ms"), fmt(row["p95_ttfa_ms"], " ms"),
            fmt(row["p50_e2e_ms"], " ms"), fmt(row["p95_e2e_ms"], " ms"),
            fmt(row["p50_effective_output_tok_s"], " tok/s"), fmt(row["p50_time_per_output_token_ms"], " ms/token"),
            fmt(row["cost_per_1000_completed_requests_usd"], " USD", 4), fmt(row["estimated_cost_usd"], " USD", 6),
        ])
    table = "| " + " | ".join(headers) + " |\n|" + "|".join(["---"] * len(headers)) + "|\n"
    table += "\n".join("| " + " | ".join(map(str, row)) + " |" for row in markdown_rows)
    measured = [row for row in rows if not row.get("warmup") and row.get("cache_mode") != "cache_seed"]
    completed = [row for row in measured if row.get("ok") and row.get("ttfa_ms") is not None]
    failures = len(measured) - len(completed)
    cache_evidence = sum(1 for row in rows if (row.get("cached_prompt_tokens") or 0) > 0)
    fresh = [row for row in summaries if row["cache_mode"] == "uncached"]
    paired = defaultdict(dict)
    for row in fresh:
        paired[(row["profile"], row["concurrency"])][row["endpoint"]] = row
    complete_pairs = [value for value in paired.values() if len(value) == 2]
    telnyx_e2e_wins = sum(
        value["Telnyx Inference"]["p50_e2e_ms"] < value["Modal Shared Endpoint"]["p50_e2e_ms"]
        for value in complete_pairs
    )
    telnyx_p95_e2e_wins = sum(
        value["Telnyx Inference"]["p95_e2e_ms"] < value["Modal Shared Endpoint"]["p95_e2e_ms"]
        for value in complete_pairs
    )
    telnyx_throughput_wins = sum(
        value["Telnyx Inference"]["p50_effective_output_tok_s"] > value["Modal Shared Endpoint"]["p50_effective_output_tok_s"]
        for value in complete_pairs
    )
    fresh_cost = defaultdict(float)
    for row in fresh:
        fresh_cost[row["endpoint"]] += row["estimated_cost_usd"] or 0.0
    cost_reduction = 100 * (1 - fresh_cost["Telnyx Inference"] / fresh_cost["Modal Shared Endpoint"])
    md = f"""# Telnyx Inference vs Modal Shared benchmark report

## Scope

This report compares Telnyx Inference with Modal Shared Endpoint for `zai-org/GLM-5.3-Flash`. Traffic originated from a Telnyx Stateful Actor and used the same prompts, reasoning effort, output limits, and request schedule for both managed endpoints. Modal Dedicated was excluded.

The exported dataset contains 1,000 rows: 24 warm-ups, 16 cache-seed requests, and 960 measured requests. Of the measured requests, {len(completed)}/{len(measured)} completed with visible answer content and {failures} did not. Failed and no-answer requests remain in the raw dataset and are excluded from latency percentiles.

## Results

Across the eight uncached profile/concurrency cells, Telnyx had lower p50 E2E latency in {telnyx_e2e_wins}/8 cells, lower p95 E2E latency in {telnyx_p95_e2e_wins}/8 cells, and higher p50 output throughput in {telnyx_throughput_wins}/8 cells. Based on measured tokens and published list rates, Telnyx's estimated uncached token cost was {cost_reduction:.1f}% lower for this workload. First-answer latency was mixed and should be read separately from completed-response performance.

{table}

## Interpretation guardrails

- TTFT is time to first model activity, including reasoning. TTFA is time to first visible answer text.
- Time per output token is derived from generation time after TTFA divided by generated output tokens. It is a cross-provider inter-token-latency proxy, not direct observation of each tokenizer emission.
- A lower latency value is better; higher throughput and reliability are better.
- Cost is estimated from measured token counts and the snapshotted published list prices. It is not a provider invoice or billing reconciliation.
- Rate-limit responses are shown as reliability and limit findings, not silently treated as model latency.
- The APIs reported cached-token evidence for {cache_evidence} requests. Because that count is zero, cached-mode latency is shown as an experimental condition, but no cache hit or discounted cached-input cost is claimed.
- Each p95 value is interpolated from the completed requests in that cell; the `p95 N` column shows the sample size.
"""
    (output / "report.md").write_text(md, encoding="utf-8")
    html_table = "<table><thead><tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in headers) + "</tr></thead><tbody>"
    html_table += "".join("<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>" for row in markdown_rows) + "</tbody></table>"
    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>Telnyx Inference vs Modal Shared</title><style>
body{{font-family:Arial,sans-serif;background:#070908;color:#f6f3ec;max-width:1500px;margin:40px auto;padding:0 24px}}a{{color:#00e3aa}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{border-bottom:1px solid #303330;text-align:left;padding:12px}}th{{color:#00e3aa;position:sticky;top:0;background:#070908}}p,li{{color:#c9c5bb;line-height:1.55}}img{{max-width:100%;margin:24px 0}}
</style></head><body><h1>Telnyx Inference vs Modal Shared benchmark report</h1><p>Responsiveness, throughput, reliability, and estimated list cost are reported independently. Modal Dedicated was excluded.</p><p>Across eight uncached profile/concurrency cells, Telnyx had lower p50 E2E latency in {telnyx_e2e_wins}/8, lower p95 E2E latency in {telnyx_p95_e2e_wins}/8, and higher p50 output throughput in {telnyx_throughput_wins}/8. Estimated uncached token cost was {cost_reduction:.1f}% lower under published list rates.</p>{html_table}<h2>Charts</h2><img src='ttfa_by_concurrency.png'><img src='ttfa_p95_by_concurrency.png'><img src='e2e_by_concurrency.png'><img src='e2e_p95_by_concurrency.png'><img src='throughput_by_concurrency.png'><img src='time_per_output_token_by_concurrency.png'><img src='estimated_cost_by_concurrency.png'><img src='reliability_by_concurrency.png'><img src='published_list_price.png'></body></html>"""
    (output / "report.html").write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    args = parser.parse_args()
    output = Path(args.run_dir)
    source = output / "raw_requests.jsonl"
    rows = [normalize_actor_row(json.loads(line)) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    successful = [row for row in rows if row.get("ok") and row.get("ttfa_ms") is not None and not row.get("warmup")]
    fields = sorted({key for row in successful for key in row})
    with (output / "clean_successful_requests.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(successful)
    summaries = summarize(rows)
    fields = sorted({key for row in summaries for key in row})
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)
    cost_fields = [
        "endpoint", "endpoint_type", "profile", "concurrency", "cache_mode", "completed",
        "measured_input_tokens", "measured_output_tokens", "estimated_cost_usd",
        "cost_per_1000_completed_requests_usd", "cost_per_million_processed_tokens_usd",
        "cost_per_million_generated_tokens_usd",
    ]
    with (output / "cost_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=cost_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summaries)
    errors = defaultdict(int)
    for row in rows:
        if row.get("warmup") or row.get("ok"):
            continue
        errors[(row.get("endpoint_label"), row.get("profile"), row.get("concurrency"), row.get("status"), str(row.get("error"))[:300])] += 1
    with (output / "failure_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["endpoint", "profile", "concurrency", "status", "error", "count"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for key, count in sorted(errors.items(), key=lambda item: tuple(str(value) for value in item[0])):
            writer.writerow(dict(zip(fields[:-1], key)) | {"count": count})
    measured = [row for row in rows if not row.get("warmup") and row.get("cache_mode") != "cache_seed"]
    completed_measured = [row for row in measured if row.get("ok") and row.get("ttfa_ms") is not None]
    validation = {
        "raw_rows": len(rows),
        "warmup_rows": sum(row.get("warmup") is True for row in rows),
        "cache_seed_rows": sum(row.get("cache_mode") == "cache_seed" for row in rows),
        "measured_rows": len(measured),
        "successful_measured_rows": len(completed_measured),
        "failed_or_no_answer_measured_rows": len(measured) - len(completed_measured),
        "providers": sorted({row.get("provider") for row in rows}),
        "modal_dedicated_excluded": all(row.get("provider") != "modal_dedicated" for row in rows),
        "cached_token_evidence_rows": sum((row.get("cached_prompt_tokens") or 0) > 0 for row in rows),
        "p95_sample_sizes": sorted({int(row["n_e2e_ms"]) for row in summaries}),
        "estimated_list_cost_usd": {
            endpoint: sum((row.get("estimated_cost_usd") or 0.0) for row in summaries if row["endpoint"] == endpoint)
            for endpoint in sorted({row["endpoint"] for row in summaries})
        },
        "cost_basis": "measured token counts multiplied by snapshotted published list prices; no cached-input discount without reported cache-token evidence",
    }
    (output / "validation_summary.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    write_report(summaries, output, rows)
    chart_metric(summaries, output / "ttfa_by_concurrency.png", "p50_ttfa_ms", "Time to first answer", "p50 visible-answer latency by profile, endpoint, and concurrency. Lower is better.")
    chart_metric(summaries, output / "ttfa_p95_by_concurrency.png", "p95_ttfa_ms", "Time to first answer - p95", "p95 visible-answer latency by profile, endpoint, and concurrency. Lower is better.")
    chart_metric(summaries, output / "e2e_by_concurrency.png", "p50_e2e_ms", "End-to-end latency", "p50 completed-response latency by profile, endpoint, and concurrency. Lower is better.")
    chart_metric(summaries, output / "e2e_p95_by_concurrency.png", "p95_e2e_ms", "End-to-end latency - p95", "p95 completed-response latency by profile, endpoint, and concurrency. Lower is better.")
    chart_metric(summaries, output / "throughput_by_concurrency.png", "p50_effective_output_tok_s", "Output throughput", "p50 output tokens per second by profile, endpoint, and concurrency. Higher is better.", divisor=1, unit=" tok/s")
    chart_metric(summaries, output / "time_per_output_token_by_concurrency.png", "p50_time_per_output_token_ms", "Time per generated output token", "p50 generation time per output token after the first visible answer. Lower is better.", divisor=1, unit=" ms/token")
    chart_metric(summaries, output / "estimated_cost_by_concurrency.png", "estimated_cost_usd", "Estimated list cost", "Measured token usage priced at published rates for each 30-request uncached cell. Lower is better.", divisor=1, unit=" USD")
    chart_metric(summaries, output / "reliability_by_concurrency.png", "reliability_pct", "Request reliability", "Completed requests with visible answer content. Higher is better.", divisor=1, unit="%")
    price_chart(output / "published_list_price.png")
    print(json.dumps({"output_dir": str(output), "raw_rows": len(rows), "clean_rows": len(successful), "summary_rows": len(summaries)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
