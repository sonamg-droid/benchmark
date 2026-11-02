import { StatefulActor } from "@telnyx/edge-runtime";

interface SessionMessage {
  role: "user" | "assistant";
  content: string;
}

interface SessionState {
  version: number;
  history: SessionMessage[];
  updatedAt: string;
}

export interface SessionTurnRequest {
  turn: number;
  user: string;
  mode: "state_only" | "native";
  expectedVersion?: number;
  model?: string;
  maxTokens?: number;
  reasoningEffort?: string;
}

interface StreamResult {
  ok: boolean;
  status: number | null;
  ttftMs: number | null;
  ttfaMs: number | null;
  e2eMs: number | null;
  content: string;
  reasoning: string;
  promptTokens: number | null;
  outputTokens: number | null;
  cachedPromptTokens: number | null;
  error: string | null;
}

interface SessionEnv {
  TELNYX_API_KEY?: string;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readUsageNumber(usage: Record<string, unknown>, key: string): number | null {
  return numberOrNull(usage[key]);
}

function cachedTokens(usage: Record<string, unknown>): number | null {
  const details = usage.prompt_tokens_details;
  if (!details || typeof details !== "object") return null;
  return numberOrNull((details as Record<string, unknown>).cached_tokens);
}

function emittedText(chunk: Record<string, unknown>): { content: string; reasoning: string } {
  let content = "";
  let reasoning = "";
  const choices = Array.isArray(chunk.choices) ? chunk.choices : [];
  for (const choice of choices) {
    if (!choice || typeof choice !== "object") continue;
    const delta = (choice as Record<string, unknown>).delta;
    if (!delta || typeof delta !== "object") continue;
    const record = delta as Record<string, unknown>;
    content += typeof record.content === "string" ? record.content : "";
    reasoning += typeof record.reasoning === "string"
      ? record.reasoning
      : typeof record.reasoning_content === "string"
        ? record.reasoning_content
        : "";
  }
  return { content, reasoning };
}

async function telnyxInference(
  request: SessionTurnRequest,
  history: SessionMessage[],
  apiKey: string,
): Promise<StreamResult> {
  const start = performance.now();
  let status: number | null = null;
  let firstActivity: number | null = null;
  let firstAnswer: number | null = null;
  let content = "";
  let reasoning = "";
  let usage: Record<string, unknown> = {};
  try {
    const response = await fetch("https://api.telnyx.com/v2/ai/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({
        model: request.model ?? "zai-org/GLM-5.3-Flash",
        messages: history,
        temperature: 0,
        max_tokens: request.maxTokens ?? 256,
        stream: true,
        stream_options: { include_usage: true },
        ...(request.reasoningEffort ? { reasoning_effort: request.reasoningEffort } : {}),
      }),
    });
    status = response.status;
    if (!response.ok) {
      const body = await response.text().catch(() => "");
      return {
        ok: false, status, ttftMs: null, ttfaMs: null, e2eMs: performance.now() - start,
        content: "", reasoning: "", promptTokens: null, outputTokens: null,
        cachedPromptTokens: null, error: body.slice(0, 800) || response.statusText,
      };
    }
    const reader = response.body?.getReader();
    if (!reader) throw new Error("Response body was not streamable");
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const raw = line.slice(5).trim();
        if (!raw || raw === "[DONE]") continue;
        let parsed: Record<string, unknown>;
        try {
          parsed = JSON.parse(raw) as Record<string, unknown>;
        } catch {
          continue;
        }
        if (parsed.usage && typeof parsed.usage === "object") {
          usage = parsed.usage as Record<string, unknown>;
        }
        const emitted = emittedText(parsed);
        if (!emitted.content && !emitted.reasoning) continue;
        const now = performance.now();
        if (firstActivity === null) firstActivity = now;
        if (firstAnswer === null && emitted.content.trim()) firstAnswer = now;
        content += emitted.content;
        reasoning += emitted.reasoning;
      }
    }
    const end = performance.now();
    return {
      ok: true,
      status,
      ttftMs: firstActivity === null ? null : firstActivity - start,
      ttfaMs: firstAnswer === null ? null : firstAnswer - start,
      e2eMs: end - start,
      content,
      reasoning,
      promptTokens: readUsageNumber(usage, "prompt_tokens"),
      outputTokens: readUsageNumber(usage, "completion_tokens"),
      cachedPromptTokens: cachedTokens(usage),
      error: null,
    };
  } catch (error) {
    return {
      ok: false, status, ttftMs: null, ttfaMs: null, e2eMs: performance.now() - start,
      content: "", reasoning: "", promptTokens: null, outputTokens: null,
      cachedPromptTokens: null, error: String(error).slice(0, 800),
    };
  }
}

export class SessionBenchmark extends StatefulActor {
  async reset(): Promise<{ ok: true; version: 0 }> {
    await this.ctx.storage.put("session", {
      version: 0,
      history: [],
      updatedAt: new Date().toISOString(),
    } satisfies SessionState);
    return { ok: true, version: 0 };
  }

  async state(): Promise<SessionState> {
    return (await this.ctx.storage.get<SessionState>("session")) ?? {
      version: 0,
      history: [],
      updatedAt: new Date().toISOString(),
    };
  }

  async turn(request: SessionTurnRequest, env: SessionEnv = {}): Promise<Record<string, unknown>> {
    const totalStart = performance.now();
    const readStart = performance.now();
    const state = await this.state();
    const stateReadMs = performance.now() - readStart;
    if (request.expectedVersion !== undefined && request.expectedVersion !== state.version) {
      return {
        ok: false,
        conflict: true,
        expectedVersion: request.expectedVersion,
        actualVersion: state.version,
        stateReadMs,
        totalMs: performance.now() - totalStart,
      };
    }

    const history = [...state.history, { role: "user" as const, content: request.user }];
    let inference: StreamResult | null = null;
    let assistant = `state-only acknowledgement for turn ${request.turn}`;
    if (request.mode === "native") {
      if (!env.TELNYX_API_KEY) {
        return { ok: false, error: "TELNYX_API_KEY is unavailable", stateReadMs };
      }
      inference = await telnyxInference(request, history, env.TELNYX_API_KEY);
      if (!inference.ok) {
        return {
          ok: false,
          error: inference.error,
          status: inference.status,
          stateReadMs,
          inference,
          totalMs: performance.now() - totalStart,
        };
      }
      assistant = inference.content;
    }

    const next: SessionState = {
      version: state.version + 1,
      history: [...history, { role: "assistant", content: assistant }],
      updatedAt: new Date().toISOString(),
    };
    const writeStart = performance.now();
    await this.ctx.storage.put("session", next);
    const stateWriteMs = performance.now() - writeStart;
    return {
      ok: true,
      turn: request.turn,
      previousVersion: state.version,
      version: next.version,
      historyMessages: next.history.length,
      stateReadMs,
      stateWriteMs,
      inference,
      totalMs: performance.now() - totalStart,
    };
  }
}
