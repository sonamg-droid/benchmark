#!/usr/bin/env python3
"""Generate Telnyx-branded charts for the inter-provider multi-turn report."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BLACK = "#080808"
CREAM = "#FEFDF5"
MUTED = "#B9B7B0"
GRID = "#41413D"
TRACK = "#242421"
GREEN = "#00E3AA"
PROVIDER_COLORS = {
    "Telnyx": GREEN,
    "Baseten": "#38A7FF",
    "Together AI": "#FF735C",
    "Fireworks": "#9B6CFF",
}
MODEL_ORDER = ("GLM 5.3 Flash", "GLM 5.3", "Kimi K3")
PROVIDER_ORDER = ("Telnyx", "Baseten", "Together AI", "Fireworks")
LOGO_CANDIDATES = (
    Path(__file__).resolve().parent / "Telnyx_Lockup_Primary_One-color_Cream_Large.png",
    Path.cwd() / "Telnyx_Lockup_Primary_One-color_Cream_Large.png",
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def header(image: Image.Image, title: str, subtitle: str) -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(image)
    logo_path = next((path for path in LOGO_CANDIDATES if path.exists()), None)
    if logo_path:
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((220, 60), Image.Resampling.LANCZOS)
        image.paste(logo, (72, 40), logo)
    else:
        draw.text((72, 42), "telnyx", font=font(36, True), fill=CREAM)
    draw.rectangle((72, 118, 168, 124), fill=GREEN)
    draw.text((72, 150), title, font=font(48, True), fill=CREAM)
    draw.text((72, 218), subtitle, font=font(22), fill=MUTED)
    return draw


def draw_grouped_bars(
    output: Path,
    rows: list[dict[str, str]],
    title: str,
    subtitle: str,
    field: str,
    formatter,
    lower_is_better: bool,
) -> None:
    image = Image.new("RGB", (1900, 1420), BLACK)
    draw = header(image, title, subtitle)
    keyed = {(row["model_family"], row["provider"]): row for row in rows}
    values = [float(row[field]) for row in rows if row.get(field)]
    scale_max = max(values) * 1.08 if values else 1
    x0, width = 610, 1040
    top, model_height, bar_gap = 335, 340, 63
    for model_index, model in enumerate(MODEL_ORDER):
        y0 = top + model_index * model_height
        draw.text((72, y0), model, font=font(31, True), fill=CREAM)
        model_rows = [keyed[(model, provider)] for provider in PROVIDER_ORDER]
        eligible = [float(row[field]) for row in model_rows if row.get(field)]
        best = (min if lower_is_better else max)(eligible) if eligible else None
        for provider_index, provider in enumerate(PROVIDER_ORDER):
            row = keyed[(model, provider)]
            y = y0 + 55 + provider_index * bar_gap
            value = float(row[field]) if row.get(field) else None
            draw.text((92, y + 4), provider, font=font(22, provider == "Telnyx"), fill=PROVIDER_COLORS[provider])
            draw.rounded_rectangle((x0, y, x0 + width, y + 34), radius=5, fill=TRACK)
            if value is not None:
                draw.rounded_rectangle((x0, y, x0 + int(width * value / scale_max), y + 34), radius=5, fill=PROVIDER_COLORS[provider])
                label = formatter(value)
                if best is not None and abs(value - best) < 1e-9:
                    label += "  best"
                draw.text((x0 + width + 24, y), label, font=font(22, True), fill=CREAM)
            else:
                draw.text((x0 + width + 24, y), "N/A", font=font(22), fill=MUTED)
        if model_index < len(MODEL_ORDER) - 1:
            draw.line((72, y0 + 312, 1828, y0 + 312), fill=GRID, width=2)
    draw.text((72, 1362), "Observed values from this benchmark sample; lower/higher direction is stated in the subtitle.", font=font(20), fill=MUTED)
    image.save(output, optimize=True)


def quality_completion(output: Path, rows: list[dict[str, str]]) -> None:
    image = Image.new("RGB", (1900, 1440), BLACK)
    draw = header(image, "Multi-turn quality and completion", "Blind quality is out of 5; judge completion is a percentage | higher is better")
    keyed = {(row["model_family"], row["provider"]): row for row in rows}
    x_quality, quality_w = 635, 500
    x_completion, completion_w = 1245, 420
    draw.text((x_quality, 292), "Blind quality", font=font(23, True), fill=CREAM)
    draw.text((x_completion, 292), "Judge completion", font=font(23, True), fill=CREAM)
    top, model_height, bar_gap = 350, 340, 63
    for model_index, model in enumerate(MODEL_ORDER):
        y0 = top + model_index * model_height
        draw.text((72, y0), model, font=font(31, True), fill=CREAM)
        model_rows = [keyed[(model, provider)] for provider in PROVIDER_ORDER]
        best_q = max(float(row["mean_blind_quality_score"]) for row in model_rows if row.get("mean_blind_quality_score"))
        best_c = max(float(row["judge_completion_rate"]) for row in model_rows if row.get("judge_completion_rate"))
        for provider_index, provider in enumerate(PROVIDER_ORDER):
            row = keyed[(model, provider)]
            y = y0 + 55 + provider_index * bar_gap
            q = float(row["mean_blind_quality_score"])
            c = float(row["judge_completion_rate"])
            color = PROVIDER_COLORS[provider]
            draw.text((92, y + 4), provider, font=font(22, provider == "Telnyx"), fill=color)
            draw.rounded_rectangle((x_quality, y, x_quality + quality_w, y + 34), radius=5, fill=TRACK)
            draw.rounded_rectangle((x_quality, y, x_quality + int(quality_w * q / 5), y + 34), radius=5, fill=color)
            q_label = f"{q:.2f}" + (" best" if abs(q - best_q) < 1e-9 else "")
            draw.text((x_quality + quality_w + 14, y), q_label, font=font(20, True), fill=CREAM)
            draw.rounded_rectangle((x_completion, y, x_completion + completion_w, y + 34), radius=5, fill=TRACK)
            draw.rounded_rectangle((x_completion, y, x_completion + int(completion_w * c / 100), y + 34), radius=5, fill=color)
            c_label = f"{c:.1f}%" + (" best" if abs(c - best_c) < 1e-9 else "")
            draw.text((x_completion + completion_w + 14, y), c_label, font=font(20, True), fill=CREAM)
        if model_index < 2:
            draw.line((72, y0 + 312, 1828, y0 + 312), fill=GRID, width=2)
    draw.text((72, 1378), "One blind judge evaluated one pass per scenario; deterministic checks and latency used all three passes.", font=font(20), fill=MUTED)
    image.save(output, optimize=True)


def reliability(output: Path, rows: list[dict[str, str]]) -> None:
    draw_grouped_bars(
        output,
        rows,
        "Multi-turn request reliability",
        "Completed conversations out of 45 attempts per provider/model cell | higher is better",
        "conversation_success_rate",
        lambda value: f"{value:.1f}%",
        False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    rows = load_rows(args.run_directory / "provider_model_summary.csv")
    output = args.run_directory / "charts"
    output.mkdir(parents=True, exist_ok=True)
    quality_completion(output / "multi-turn-quality-completion.png", rows)
    draw_grouped_bars(
        output / "multi-turn-p50-conversation-latency.png",
        rows,
        "Multi-turn median response time",
        "Median total model response time across a complete conversation | seconds, lower is better",
        "p50_total_response_ms",
        lambda value: f"{value / 1000:.2f}s",
        True,
    )
    draw_grouped_bars(
        output / "multi-turn-p95-conversation-latency.png",
        rows,
        "Multi-turn tail response time",
        "Observed p95 total model response time across a complete conversation | seconds, lower is better",
        "p95_total_response_ms",
        lambda value: f"{value / 1000:.2f}s",
        True,
    )
    draw_grouped_bars(
        output / "multi-turn-p50-ttft.png",
        rows,
        "Time to first model activity",
        "Median TTFT across successful model turns | seconds, lower is better",
        "p50_ttft_ms",
        lambda value: f"{value / 1000:.2f}s",
        True,
    )
    draw_grouped_bars(
        output / "multi-turn-p50-ttfa.png",
        rows,
        "Time to first visible answer",
        "Median TTFA across successful model turns | seconds, lower is better",
        "p50_ttfa_ms",
        lambda value: f"{value / 1000:.2f}s",
        True,
    )
    reliability(output / "multi-turn-reliability.png", rows)
    draw_grouped_bars(
        output / "multi-turn-objective-checks.png",
        rows,
        "Deterministic constraint checks",
        "Required-field, JSON, and constraint checks passed | percentage, higher is better",
        "objective_check_rate",
        lambda value: f"{value:.1f}%",
        False,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
