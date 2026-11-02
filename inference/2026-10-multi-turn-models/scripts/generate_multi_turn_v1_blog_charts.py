#!/usr/bin/env python3
"""Generate Telnyx-branded charts for the multi-turn benchmark v1 blog."""

from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data"
OUT = ROOT / "report" / "assets"
LOGO = OUT / "telnyx-logo.png"

BLACK = "#080808"
CREAM = "#FEFDF5"
MUTED = "#B9B7B0"
GRID = "#41413D"
TRACK = "#242421"
GREEN = "#00E3AA"
COLORS = {
    "GLM 5.3 Flash": GREEN,
    "GLM 5.3": "#38A7FF",
    "Kimi K3": "#9B6CFF",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def branded_header(image: Image.Image, title: str, subtitle: str) -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(image)
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        logo.thumbnail((220, 60), Image.Resampling.LANCZOS)
        image.paste(logo, (72, 40), logo)
    else:
        draw.text((72, 42), "telnyx", font=font(36, True), fill=CREAM)
    draw.rectangle((72, 118, 168, 124), fill=GREEN)
    draw.text((72, 150), title, font=font(50, True), fill=CREAM)
    draw.text((72, 220), subtitle, font=font(23), fill=MUTED)
    return draw


def featured_image() -> None:
    image = Image.new("RGB", (1800, 945), BLACK)
    draw = ImageDraw.Draw(image)
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        logo.thumbnail((250, 72), Image.Resampling.LANCZOS)
        image.paste(logo, (84, 58), logo)
    else:
        draw.text((84, 62), "telnyx", font=font(40, True), fill=CREAM)

    draw.rectangle((84, 166, 198, 173), fill=GREEN)
    draw.text((84, 214), "Multi-turn LLM benchmark", font=font(70, True), fill=CREAM)
    draw.text((84, 306), "Speed vs. task completion", font=font(70, True), fill=CREAM)
    draw.text(
        (84, 420),
        "GLM 5.3 Flash, GLM 5.3, and Kimi K3 tested on fixed four-turn workflows",
        font=font(28),
        fill=MUTED,
    )

    stats = [
        ("15", "scenarios"),
        ("180", "model turns"),
        ("3", "models"),
    ]
    x = 84
    for value, label in stats:
        draw.rounded_rectangle((x, 565, x + 470, 770), radius=8, fill=TRACK, outline=GRID, width=2)
        draw.text((x + 34, 596), value, font=font(62, True), fill=GREEN)
        draw.text((x + 34, 684), label, font=font(27, True), fill=CREAM)
        x += 520

    draw.text((84, 862), "Quality, completion, reliability, and latency measured separately", font=font(25), fill=MUTED)
    image.save(OUT / "multi-turn-llm-benchmark.png", optimize=True)


def completion_chart(model_rows: list[dict[str, str]]) -> None:
    image = Image.new("RGB", (1800, 980), BLACK)
    draw = branded_header(
        image,
        "Multi-turn completion",
        "15 four-turn scenarios per model | percentage, higher is better",
    )
    ordered = sorted(model_rows, key=lambda row: (row["model"] != "GLM 5.3 Flash", row["model"]))
    ordered = [next(row for row in model_rows if row["model"] == name) for name in ("GLM 5.3 Flash", "GLM 5.3", "Kimi K3")]
    x0, width = 550, 1000
    top, group_h = 350, 185
    for idx, row in enumerate(ordered):
        y = top + idx * group_h
        model = row["model"]
        color = COLORS[model]
        draw.text((72, y + 28), model, font=font(29, True), fill=CREAM)
        values = [
            ("Judge completion", float(row["judge_completion_rate"].rstrip("%"))),
            ("Objective checks", float(row["objective_check_rate"].rstrip("%"))),
        ]
        for sub, (label, value) in enumerate(values):
            yy = y + sub * 66
            draw.text((310, yy + 10), label, font=font(22), fill=MUTED)
            draw.rounded_rectangle((x0, yy + 8, x0 + width, yy + 43), radius=5, fill=TRACK)
            draw.rounded_rectangle((x0, yy + 8, x0 + int(width * value / 100), yy + 43), radius=5, fill=color)
            draw.text((x0 + width + 25, yy + 6), f"{value:.1f}%", font=font(25, True), fill=CREAM)
        if idx < 2:
            draw.line((72, y + 155, 1728, y + 155), fill=GRID, width=2)
    draw.text((72, 901), "All three models completed 15/15 conversations and 60/60 model turns.", font=font(22), fill=CREAM)
    draw.text((72, 936), "Judge completion is a binary decision from two judges; objective checks are deterministic rules.", font=font(20), fill=MUTED)
    image.save(OUT / "multi-turn-completion-checks.png", optimize=True)


def quality_chart(quality_rows: list[dict[str, str]]) -> None:
    image = Image.new("RGB", (1900, 1230), BLACK)
    draw = branded_header(
        image,
        "Blind quality scores",
        "Average points out of 5 across 15 scenarios | higher is better",
    )
    columns = [
        ("task_completion", "Task\ncompletion"),
        ("correctness", "Correctness"),
        ("state_tracking", "State\ntracking"),
        ("correction_following", "Corrections"),
        ("final_answer_usability", "Usability"),
    ]
    row_order = [
        ("GLM 5.3 Flash", "DeepSeek V4.1 Flash"),
        ("GLM 5.3 Flash", "MiniMax M3"),
        ("GLM 5.3", "DeepSeek V4.1 Flash"),
        ("GLM 5.3", "MiniMax M3"),
        ("Kimi K3", "DeepSeek V4.1 Flash"),
        ("Kimi K3", "MiniMax M3"),
    ]
    keyed = {(row["model"], row["judge"]): row for row in quality_rows}
    label_x, grid_x, cell_w = 72, 610, 232
    top, row_h, cell_h = 390, 112, 78
    for col, (_, label) in enumerate(columns):
        x = grid_x + col * cell_w
        draw.multiline_text((x + 10, 300), label, font=font(23, True), fill=CREAM, spacing=3)
    for idx, key in enumerate(row_order):
        row = keyed[key]
        model, judge = key
        y = top + idx * row_h
        draw.text((label_x, y + 2), model, font=font(27, True), fill=COLORS[model])
        draw.text((label_x, y + 39), f"Judge: {judge}", font=font(20), fill=MUTED)
        for col, (field, _) in enumerate(columns):
            value = float(row[field])
            x = grid_x + col * cell_w
            intensity = max(0.0, min(1.0, (value - 3.5) / 1.5))
            base = (22, 46, 40)
            peak = (0, 133, 101)
            fill = tuple(round(base[i] + (peak[i] - base[i]) * intensity) for i in range(3))
            draw.rounded_rectangle((x, y, x + cell_w - 14, y + cell_h), radius=7, fill=fill, outline=GRID, width=1)
            text = f"{value:.2f} / 5"
            bbox = draw.textbbox((0, 0), text, font=font(27, True))
            tx = x + (cell_w - 14 - (bbox[2] - bbox[0])) / 2
            draw.text((tx, y + 23), text, font=font(27, True), fill=CREAM)
        if idx in (1, 3):
            draw.line((72, y + 96, 1828, y + 96), fill=GRID, width=2)
    draw.text((72, 1126), "Candidate model names were omitted from judge prompts.", font=font(21), fill=CREAM)
    draw.text((72, 1162), "DeepSeek V4.1 Flash and MiniMax M3 scored every completed conversation independently.", font=font(20), fill=MUTED)
    image.save(OUT / "multi-turn-quality-scores.png", optimize=True)


def latency_chart(model_rows: list[dict[str, str]]) -> None:
    image = Image.new("RGB", (1800, 1040), BLACK)
    draw = branded_header(
        image,
        "Total conversation response time",
        "Sum of four model-turn E2E times | seconds, lower is better",
    )
    ordered = [next(row for row in model_rows if row["model"] == name) for name in ("GLM 5.3 Flash", "GLM 5.3", "Kimi K3")]
    values = []
    for row in ordered:
        values.extend([float(row["p50_total_response_ms"]) / 1000, float(row["p95_total_response_ms"]) / 1000])
    scale_max = max(values) * 1.08
    x0, width = 550, 1000
    top, group_h = 350, 200
    for idx, row in enumerate(ordered):
        y = top + idx * group_h
        model = row["model"]
        color = COLORS[model]
        draw.text((72, y + 30), model, font=font(29, True), fill=CREAM)
        for sub, (label, field) in enumerate((('p50', 'p50_total_response_ms'), ('observed p95', 'p95_total_response_ms'))):
            yy = y + sub * 70
            value = float(row[field]) / 1000
            draw.text((330, yy + 10), label, font=font(22), fill=MUTED)
            draw.rounded_rectangle((x0, yy + 8, x0 + width, yy + 43), radius=5, fill=TRACK)
            draw.rounded_rectangle((x0, yy + 8, x0 + int(width * value / scale_max), yy + 43), radius=5, fill=color)
            draw.text((x0 + width + 25, yy + 6), f"{value:.2f} s", font=font(25, True), fill=CREAM)
        if idx < 2:
            draw.line((72, y + 167, 1728, y + 167), fill=GRID, width=2)
    draw.text((72, 948), "n=15 conversations per model. Observed p95 is sample-specific and is not an SLA.", font=font(21), fill=MUTED)
    image.save(OUT / "multi-turn-conversation-latency.png", optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    model_rows = rows(RUN / "model_summary.csv")
    quality_rows = rows(RUN / "quality_by_judge.csv")
    featured_image()
    completion_chart(model_rows)
    quality_chart(quality_rows)
    latency_chart(model_rows)
    print(OUT)


if __name__ == "__main__":
    main()
