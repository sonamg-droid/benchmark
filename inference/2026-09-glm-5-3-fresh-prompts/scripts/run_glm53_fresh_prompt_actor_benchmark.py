#!/usr/bin/env python3
"""Run reproducible, non-identical GLM 5.3 prompts through the benchmark actor."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import socket
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse

from run_glm53_public_provider_actor_benchmark import (
    DEFAULT_BASE_URL,
    PROVIDERS,
    PROMPT_DIR,
    TEXT_FIELDS,
    parse_prompt,
    request_json,
    request_text,
    write_clean_metrics_csv,
    write_status,
)


PROFILES = (
    "01_1k_in_100_out",
    "02_1k_in_1k_out",
    "03_10k_in_100_out",
    "04_10k_in_1k_out",
    "05_100k_in_100_out",
    "06_100k_in_1k_out",
)


def retry_read(call, label: str):
    deadline = time.monotonic() + 1800
    while True:
        try:
            return call()
        except (TimeoutError, URLError, ConnectionResetError) as exc:
            if time.monotonic() >= deadline:
                raise
            print(json.dumps({"waiting_for_actor": label, "error": str(exc)[:200]}), flush=True)
            time.sleep(10)


def varied_passage(fixture: str, seed: int) -> str:
    paragraphs = [part.strip() for part in fixture.split("\n\n") if part.strip()]
    if len(paragraphs) < 2:
        raise ValueError("Fixture needs at least two paragraphs")
    rng = random.Random(seed)
    varied: list[str] = []
    for start in range(0, len(paragraphs), 8):
        group = paragraphs[start : start + 8]
        rng.shuffle(group)
        varied.extend(group)
    return "\n\n".join(varied)


def build_variants(profile_name: str, count: int) -> tuple[list[dict], list[dict]]:
    original = parse_prompt(PROMPT_DIR / f"{profile_name}.md")
    marker = original["user"].find("\n---\n")
    if marker < 0:
        raise ValueError(f"Missing passage separator in {profile_name}")
    instructions = original["user"][:marker]
    passage = original["user"][marker + len("\n---\n") :]
    variants: list[dict] = []
    manifest: list[dict] = []
    for iteration in range(1, count + 1):
        variant_name = f"{profile_name}_fresh_{iteration:02d}"
        seed = int(hashlib.sha256(f"2026-09-17:{variant_name}".encode()).hexdigest()[:16], 16)
        variant = dict(original)
        variant["name"] = variant_name
        variant["user"] = (
            f"Passage selection: {variant_name}.\n\n"
            f"{instructions}\n---\n{varied_passage(passage, seed)}"
        )
        variants.append(variant)
        manifest.append(
            {
                "profile": profile_name,
                "variant": variant_name,
                "seed": seed,
                "user_sha256": hashlib.sha256(variant["user"].encode()).hexdigest(),
                "user_chars": len(variant["user"]),
                "user_words": len(variant["user"].split()),
                "max_tokens": variant["maxTokens"],
            }
        )
    return variants, manifest


def export_run(base: str, run_id: str, out_dir: Path) -> int:
    raw_path = out_dir / f"{run_id}.raw-results-with-text.csv"
    raw_path.write_text(retry_read(lambda: request_text(f"{base}/runs/{run_id}/results.csv"), f"{run_id}:csv"))
    clean_path = out_dir / f"{run_id}.clean-metrics.csv"
    count = write_clean_metrics_csv(raw_path, clean_path)
    json_path = out_dir / f"{run_id}.raw-results-with-text.json"
    json_path.write_text(json.dumps(retry_read(lambda: request_json(f"{base}/runs/{run_id}/results.json"), f"{run_id}:json"), indent=2))
    return count


def combine(out_dir: Path, run_ids: list[str]) -> None:
    rows: list[dict] = []
    for run_id in run_ids:
        with (out_dir / f"{run_id}.raw-results-with-text.csv").open(newline="") as handle:
            rows.extend(csv.DictReader(handle))
    if len(rows) != 240:
        raise RuntimeError(f"Expected 240 rows, got {len(rows)}")
    keys = {(r["provider"], r["profile"]) for r in rows}
    if len(keys) != 240:
        raise RuntimeError(f"Expected 240 unique provider/variant pairs, got {len(keys)}")
    raw_path = out_dir / "glm53-fresh-prompts-20260917.raw-results-with-text.csv"
    fields = list(rows[0])
    with raw_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    write_clean_metrics_csv(raw_path, out_dir / "glm53-fresh-prompts-20260917.clean-metrics.csv")
    (out_dir / "glm53-fresh-prompts-20260917.raw-results-with-text.json").write_text(
        json.dumps(rows, indent=2)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--out-dir", type=Path, default=Path("output/glm53-fresh-prompts"))
    parser.add_argument("--variants", type=int, default=10)
    parser.add_argument("--profiles", nargs="*", choices=PROFILES, default=list(PROFILES))
    parser.add_argument("--poll-interval", type=float, default=10)
    parser.add_argument("--actor-ip", help="Connect to this regional ingress IP while verifying the original HTTPS hostname")
    args = parser.parse_args()
    if not args.base_url:
        parser.error("set BENCHMARK_ACTOR_URL or pass --base-url")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")
    if args.actor_ip:
        actor_host = urlparse(base).hostname
        original_getaddrinfo = socket.getaddrinfo

        def actor_getaddrinfo(host, port, *other_args, **other_kwargs):
            target = args.actor_ip if host == actor_host else host
            return original_getaddrinfo(target, port, *other_args, **other_kwargs)

        socket.getaddrinfo = actor_getaddrinfo
        print(json.dumps({"actor_host": actor_host, "connected_via_ip": args.actor_ip}), flush=True)
    all_variants: list[dict] = []
    manifest: list[dict] = []
    run_ids: list[str] = []

    for profile_name in args.profiles:
        variants, entries = build_variants(profile_name, args.variants)
        all_variants.extend(variants)
        manifest.extend(entries)
    (args.out_dir / "prompt_manifest.json").write_text(json.dumps(manifest, indent=2))
    (args.out_dir / "prompts.json").write_text(json.dumps(all_variants, indent=2))

    for profile_name in args.profiles:
        variants = [p for p in all_variants if p["name"].startswith(profile_name + "_fresh_")]
        chunks = [[variant] for variant in variants] if "_100k_" in profile_name else [variants]
        for chunk in chunks:
            run_id = f"glm53-fresh-20260917-{profile_name.replace('_', '-')}"
            if "_100k_" in profile_name:
                run_id += f"-full-{chunk[0]['name'].rsplit('_', 1)[-1]}"
            run_ids.append(run_id)
            out_path = args.out_dir / f"{run_id}.raw-results-with-text.csv"
            if out_path.exists():
                print(json.dumps({"run_id": run_id, "already_exported": True}), flush=True)
                continue
            payload = {
                "repeats": 1,
                "timeoutMs": 900_000,
                "batchSize": 1,
                "tokenUsageProbe": True,
                "autoStart": True,
                "profiles": chunk,
                "suites": [{"suite": "glm_53", "providers": PROVIDERS}],
            }
            (args.out_dir / f"{run_id}.payload.json").write_text(json.dumps(payload, indent=2))
            status_url = f"{base}/runs/{run_id}/status"
            status = retry_read(lambda: request_json(status_url), f"{run_id}:initial_status")
            if not status.get("ok"):
                started = request_json(f"{base}/runs/{run_id}/start", method="POST", payload=payload)
                print(json.dumps({"run_id": run_id, "start": started}), flush=True)
            last_completed = -1
            while True:
                status = retry_read(lambda: request_json(status_url), f"{run_id}:status")
                write_status(args.out_dir / f"{run_id}.status.json", status)
                completed = int(status.get("completed", 0))
                if completed != last_completed or status.get("done"):
                    print(json.dumps({"run_id": run_id, "completed": completed, "total": status.get("total"), "failures": status.get("failures"), "done": status.get("done")}), flush=True)
                    last_completed = completed
                if status.get("done"):
                    break
                time.sleep(args.poll_interval)
            exported_rows = export_run(base, run_id, args.out_dir)
            print(json.dumps({"run_id": run_id, "exported_rows": exported_rows}), flush=True)
            with (args.out_dir / f"{run_id}.clean-metrics.csv").open(newline="") as handle:
                credit_errors = [row for row in csv.DictReader(handle) if row["status"] == "402"]
            if credit_errors:
                raise SystemExit(f"Stopped after {run_id}: provider returned HTTP 402; restore credits before resuming")

    if len(run_ids) == 24 and args.variants == 10:
        combine(args.out_dir, run_ids)
        print(json.dumps({"combined_rows": 240, "out_dir": str(args.out_dir)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
