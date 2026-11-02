# Inference benchmarks

Inference model and provider benchmarks run by Telnyx staff. Each run is self-contained and follows the layout in the [root README](../README.md).

## Runs

| Run | Measured | Headline | Platforms |
|---|---|---|---|
| [`2026-09-glm-5-3-fresh-prompts/`](2026-09-glm-5-3-fresh-prompts/) | GLM 5.3 latency across four providers using distinct prompts | Telnyx had the lowest median completed-response latency in 5 of 6 profiles | Telnyx, Baseten, Together AI, Fireworks |
| [`2026-10-multi-turn-models/`](2026-10-multi-turn-models/) | Three open-weight models on fixed multi-turn workflows | All models completed 15/15 conversations; speed and judged completion differed | Telnyx Inference |
| [`2026-10-multi-turn-providers/`](2026-10-multi-turn-providers/) | Three model families across four providers on multi-turn workflows | Telnyx recorded the lowest median and observed p95 conversation response time for all three model families | Telnyx, Baseten, Together AI, Fireworks |
| [`2026-10-glm-5-3-flash-modal/`](2026-10-glm-5-3-flash-modal/) | GLM 5.3 Flash managed endpoint comparison | Telnyx completed responses faster; Modal Shared had stronger p95 first-visible-answer latency in most cells | Telnyx, Modal Shared |
