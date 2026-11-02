import { StatefulActor } from "@telnyx/edge-runtime";

type MessageRole = "system" | "user" | "assistant";

interface ChatMessage {
  role: MessageRole;
  content: string;
}

interface ModelConfig {
  id: string;
  label: string;
  baseUrl: string;
  apiKeyEnv: string;
  maxTokensField?: "max_tokens" | "max_completion_tokens";
  reasoningEffort?: string;
  judgeMaxTokens?: number;
  extraBody?: Record<string, unknown>;
}

interface ScenarioTurn {
  id: string;
  user: string;
  maxTokens: number;
}

type ObjectiveCheck =
  | { type: "contains_all"; values: string[]; label: string; caseSensitive?: boolean }
  | { type: "contains_none"; values: string[]; label: string; caseSensitive?: boolean }
  | { type: "regex"; pattern: string; label: string; flags?: string }
  | { type: "valid_json"; label: string }
  | { type: "json_has_keys"; keys: string[]; label: string };

interface Scenario {
  id: string;
  category: "developer" | "business" | "planning_editing_structured";
  title: string;
  system: string;
  judgeContext: string;
  turns: ScenarioTurn[];
  objectiveChecks: ObjectiveCheck[];
}

interface StartRequest {
  datasetVersion: string;
  models: ModelConfig[];
  judges: ModelConfig[];
  scenarios: Scenario[];
  repeats?: number;
  timeoutMs?: number;
  batchSize?: number;
  autoStart?: boolean;
}

interface ConversationTask {
  model: ModelConfig;
  scenario: Scenario;
  repeat: number;
}

interface TurnResult {
  turn_id: string;
  turn_index: number;
  user_text: string;
  ok: boolean;
  status: number | null;
  started_at: string;
  e2e_ms: number | null;
  ttft_ms: number | null;
  ttfr_ms: number | null;
  ttfa_ms: number | null;
  first_delta_kind: "reasoning" | "content" | "mixed" | null;
  finish_reason: string | null;
  reasoning_text: string;
  content_text: string;
  prompt_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  error: string | null;
}

interface ObjectiveCheckResult {
  label: string;
  type: ObjectiveCheck["type"];
  passed: boolean;
  detail: string;
}

interface JudgeScores {
  task_completion: number;
  correctness: number;
  state_tracking: number;
  correction_following: number;
  final_answer_usability: number;
}

interface JudgeResult {
  judge_model: string;
  judge_label: string;
  ok: boolean;
  status: number | null;
  finish_reason: string | null;
  scores: JudgeScores | null;
  completed: boolean | null;
  summary: string | null;
  strengths: string[];
  issues: string[];
  raw_response: string;
  error: string | null;
}

interface ConversationResult {
  conversation_id: string;
  dataset_version: string;
  scenario_id: string;
  scenario_title: string;
  category: Scenario["category"];
  model: string;
  model_label: string;
  repeat: number;
  started_at: string;
  finished_at: string;
  ok: boolean;
  completed_turns: number;
  expected_turns: number;
  request_failures: number;
  total_response_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  turns: TurnResult[];
  objective_checks: ObjectiveCheckResult[];
  judges: JudgeResult[];
}

interface RunState {
  datasetVersion: string;
  startedAt: string;
  finishedAt?: string;
  models: ModelConfig[];
  judges: ModelConfig[];
  scenarios: Scenario[];
  repeats: number;
  timeoutMs: number;
  batchSize: number;
  autoStart: boolean;
  total: number;
  cursor: number;
  successes: number;
  failures: number;
  lastAlarmAt?: string;
}

interface RejudgeTask {
  resultIndex: number;
  judgeIndex: number;
}

interface RejudgeState {
  startedAt: string;
  finishedAt?: string;
  total: number;
  cursor: number;
  successes: number;
  failures: number;
  tasks: RejudgeTask[];
  judges: ModelConfig[];
  lastAlarmAt?: string;
}

interface EnvLike {
  TELNYX_API_KEY?: string;
  [key: string]: unknown;
}

interface StreamResult {
  ok: boolean;
  status: number | null;
  startedAt: string;
  e2eMs: number | null;
  ttftMs: number | null;
  ttfrMs: number | null;
  ttfaMs: number | null;
  firstDeltaKind: "reasoning" | "content" | "mixed" | null;
  finishReason: string | null;
  reasoningText: string;
  contentText: string;
  promptTokens: number | null;
  outputTokens: number | null;
  totalTokens: number | null;
  error: string | null;
}

const SCORE_FIELDS: (keyof JudgeScores)[] = [
  "task_completion",
  "correctness",
  "state_tracking",
  "correction_following",
  "final_answer_usability",
];

function nowIso(): string {
  return new Date().toISOString();
}

function compactError(value: unknown): string {
  if (typeof value === "string") return value.slice(0, 1200);
  try {
    return JSON.stringify(value).slice(0, 1200);
  } catch {
    return String(value).slice(0, 1200);
  }
}

function csvEscape(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  if (/[",\n\r]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function sumNullable(values: Array<number | null>): number | null {
  const present = values.filter((value): value is number => value !== null);
  return present.length === values.length ? present.reduce((sum, value) => sum + value, 0) : null;
}

function resultKey(index: number): string {
  return `result:${String(index).padStart(6, "0")}`;
}

function validateRequest(request: StartRequest): void {
  if (!request.datasetVersion?.trim()) throw new Error("datasetVersion is required");
  if (!request.models?.length) throw new Error("models are required");
  if (!request.judges?.length) throw new Error("judges are required");
  if (!request.scenarios?.length) throw new Error("scenarios are required");

  const scenarioIds = new Set<string>();
  for (const scenario of request.scenarios) {
    if (!scenario.id || scenarioIds.has(scenario.id)) {
      throw new Error(`Scenario IDs must be non-empty and unique: ${scenario.id}`);
    }
    scenarioIds.add(scenario.id);
    if (scenario.turns.length < 4 || scenario.turns.length > 6) {
      throw new Error(`${scenario.id} must contain 4 to 6 turns`);
    }
    for (const turn of scenario.turns) {
      if (!turn.id || !turn.user || !Number.isFinite(turn.maxTokens) || turn.maxTokens <= 0) {
        throw new Error(`Invalid turn in ${scenario.id}`);
      }
    }
  }
}

function taskAtIndex(state: RunState, index: number): ConversationTask {
  let offset = index;
  for (const model of state.models) {
    for (const scenario of state.scenarios) {
      for (let repeat = 1; repeat <= state.repeats; repeat += 1) {
        if (offset === 0) return { model, scenario, repeat };
        offset -= 1;
      }
    }
  }
  throw new Error(`Task index out of range: ${index}`);
}

function extractEmittedText(chunk: Record<string, unknown>): { content: string; reasoning: string } {
  let content = "";
  let reasoning = "";
  const choices = Array.isArray(chunk.choices) ? chunk.choices : [];
  for (const choice of choices) {
    const delta = choice && typeof choice === "object" ? (choice as Record<string, unknown>).delta : null;
    if (!delta || typeof delta !== "object") continue;
    const record = delta as Record<string, unknown>;
    content += typeof record.content === "string" ? record.content : "";
    reasoning +=
      typeof record.reasoning === "string"
        ? record.reasoning
        : typeof record.reasoning_content === "string"
          ? record.reasoning_content
          : "";
  }
  return { content, reasoning };
}

async function streamCompletion(
  model: ModelConfig,
  messages: ChatMessage[],
  maxTokens: number,
  env: EnvLike,
  timeoutMs: number,
): Promise<StreamResult> {
  const apiKey = env[model.apiKeyEnv];
  const startedAt = nowIso();
  if (typeof apiKey !== "string" || !apiKey) {
    return failedStream(startedAt, null, `Missing ${model.apiKeyEnv}`);
  }

  const payload: Record<string, unknown> = {
    model: model.id,
    messages,
    temperature: 0,
    stream: true,
    stream_options: { include_usage: true },
    [model.maxTokensField ?? "max_tokens"]: maxTokens,
    ...(model.reasoningEffort ? { reasoning_effort: model.reasoningEffort } : {}),
    ...(model.extraBody ?? {}),
  };
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort("timeout"), timeoutMs);
  const start = performance.now();
  let status: number | null = null;
  let firstAny: number | null = null;
  let firstReasoning: number | null = null;
  let firstAnswer: number | null = null;
  let firstDeltaKind: StreamResult["firstDeltaKind"] = null;
  let finishReason: string | null = null;
  let reasoningText = "";
  let contentText = "";
  let usage: Record<string, unknown> = {};

  try {
    const response = await fetch(`${model.baseUrl.replace(/\/$/, "")}/chat/completions`, {
      method: "POST",
      signal: abort.signal,
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(payload),
    });
    status = response.status;
    if (!response.ok) {
      const body = await response.text().catch(() => "");
      return failedStream(startedAt, status, body || response.statusText);
    }

    const reader = response.body?.getReader();
    if (!reader) return failedStream(startedAt, status, "Response body was not streamable");
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
        const event = line.slice(5).trim();
        if (!event || event === "[DONE]") continue;
        let chunk: Record<string, unknown>;
        try {
          chunk = JSON.parse(event) as Record<string, unknown>;
        } catch {
          continue;
        }
        if (chunk.usage && typeof chunk.usage === "object") {
          usage = chunk.usage as Record<string, unknown>;
        }
        const emitted = extractEmittedText(chunk);
        const choices = Array.isArray(chunk.choices) ? chunk.choices : [];
        for (const choice of choices) {
          if (!choice || typeof choice !== "object") continue;
          const value = (choice as Record<string, unknown>).finish_reason;
          if (typeof value === "string") finishReason = value;
        }
        if (!emitted.content && !emitted.reasoning) continue;
        const now = performance.now();
        if (firstAny === null) {
          firstAny = now;
          firstDeltaKind = emitted.content && emitted.reasoning
            ? "mixed"
            : emitted.content
              ? "content"
              : "reasoning";
        }
        if (emitted.reasoning && firstReasoning === null) firstReasoning = now;
        if (emitted.content.trim() && firstAnswer === null) firstAnswer = now;
        reasoningText += emitted.reasoning;
        contentText += emitted.content;
      }
    }
  } catch (error) {
    return failedStream(startedAt, status, compactError(error));
  } finally {
    clearTimeout(timer);
  }

  const end = performance.now();
  const noVisibleAnswer = !contentText.trim();
  return {
    ok: !noVisibleAnswer,
    status,
    startedAt,
    e2eMs: end - start,
    ttftMs: firstAny === null ? null : firstAny - start,
    ttfrMs: firstReasoning === null ? null : firstReasoning - start,
    ttfaMs: firstAnswer === null ? null : firstAnswer - start,
    firstDeltaKind,
    finishReason,
    reasoningText,
    contentText,
    promptTokens: numberOrNull(usage.prompt_tokens),
    outputTokens: numberOrNull(usage.completion_tokens),
    totalTokens: numberOrNull(usage.total_tokens),
    error: noVisibleAnswer
      ? `No visible answer content was emitted (finish_reason=${finishReason ?? "unknown"})`
      : null,
  };
}

function failedStream(startedAt: string, status: number | null, error: string): StreamResult {
  return {
    ok: false,
    status,
    startedAt,
    e2eMs: null,
    ttftMs: null,
    ttfrMs: null,
    ttfaMs: null,
    firstDeltaKind: null,
    finishReason: null,
    reasoningText: "",
    contentText: "",
    promptTokens: null,
    outputTokens: null,
    totalTokens: null,
    error: compactError(error),
  };
}

function parseJsonObject(text: string): Record<string, unknown> | null {
  const trimmed = text.trim();
  const candidates = [trimmed];
  const thinkEnd = trimmed.lastIndexOf("</mm:think>");
  if (thinkEnd >= 0) candidates.push(trimmed.slice(thinkEnd + "</mm:think>".length).trim());
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced?.[1]) candidates.push(fenced[1].trim());
  const objectStart = trimmed.indexOf("{");
  const objectEnd = trimmed.lastIndexOf("}");
  if (objectStart >= 0 && objectEnd > objectStart) {
    candidates.push(trimmed.slice(objectStart, objectEnd + 1));
  }
  for (const candidate of candidates) {
    try {
      const parsed = JSON.parse(candidate);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
    } catch {
      // Try the next extraction strategy.
    }
  }
  return null;
}

function boundedScore(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 1 || value > 5) return null;
  return value;
}

function parseJudgeScores(value: unknown): JudgeScores | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  const scores = {} as JudgeScores;
  for (const field of SCORE_FIELDS) {
    const score = boundedScore(record[field]);
    if (score === null) return null;
    scores[field] = score;
  }
  return scores;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function transcriptForJudge(scenario: Scenario, turns: TurnResult[]): string {
  const lines: string[] = [];
  for (const turn of turns) {
    lines.push(`USER (${turn.turn_id}):\n${turn.user_text}`);
    lines.push(`ASSISTANT (${turn.turn_id}):\n${turn.content_text}`);
  }
  return lines.join("\n\n");
}

async function judgeConversation(
  judge: ModelConfig,
  scenario: Scenario,
  turns: TurnResult[],
  objectiveChecks: ObjectiveCheckResult[],
  env: EnvLike,
  timeoutMs: number,
): Promise<JudgeResult> {
  const prompt = [
    "You are a strict, blind evaluator of a multi-turn assistant conversation.",
    "The candidate model identity is intentionally hidden. Judge only the supplied evidence.",
    "Score each dimension from 1 (poor) to 5 (excellent): task_completion, correctness, state_tracking, correction_following, final_answer_usability.",
    "Task completion asks whether the final response satisfies the full accumulated request.",
    "Correctness asks whether claims and transformations are supported by the scenario.",
    "State tracking asks whether earlier facts and constraints remain consistent across turns.",
    "Correction following asks whether later corrections replace conflicting earlier instructions.",
    "Final answer usability asks whether the final response is directly usable in the requested form.",
    "Return JSON only with this shape:",
    '{"completed":true,"scores":{"task_completion":1,"correctness":1,"state_tracking":1,"correction_following":1,"final_answer_usability":1},"summary":"...","strengths":["..."],"issues":["..."]}',
    "Do not mention or guess the model or provider.",
    `SCENARIO TITLE:\n${scenario.title}`,
    `EVALUATION CONTEXT:\n${scenario.judgeContext}`,
    `OBJECTIVE CHECK RESULTS:\n${JSON.stringify(objectiveChecks)}`,
    `CONVERSATION:\n${transcriptForJudge(scenario, turns)}`,
  ].join("\n\n");
  const response = await streamCompletion(
    judge,
    [
      { role: "system", content: "Evaluate faithfully and emit valid JSON only." },
      { role: "user", content: prompt },
    ],
    judge.judgeMaxTokens ?? 4096,
    env,
    timeoutMs,
  );
  if (!response.ok) {
    return {
      judge_model: judge.id,
      judge_label: judge.label,
      ok: false,
      status: response.status,
      finish_reason: response.finishReason,
      scores: null,
      completed: null,
      summary: null,
      strengths: [],
      issues: [],
      raw_response: response.contentText,
      error: response.error,
    };
  }
  const parsed = parseJsonObject(response.contentText);
  const scores = parseJudgeScores(parsed?.scores);
  const completed = typeof parsed?.completed === "boolean" ? parsed.completed : null;
  const parseError = !parsed || !scores || completed === null ? "Judge response did not match the required JSON schema" : null;
  return {
    judge_model: judge.id,
    judge_label: judge.label,
    ok: parseError === null,
    status: response.status,
    finish_reason: response.finishReason,
    scores,
    completed,
    summary: typeof parsed?.summary === "string" ? parsed.summary : null,
    strengths: stringArray(parsed?.strengths),
    issues: stringArray(parsed?.issues),
    raw_response: response.contentText,
    error: parseError,
  };
}

function extractJson(text: string): unknown {
  const parsed = parseJsonObject(text);
  return parsed ?? undefined;
}

function runObjectiveChecks(checks: ObjectiveCheck[], finalAnswer: string): ObjectiveCheckResult[] {
  return checks.map((check) => {
    try {
      if (check.type === "valid_json") {
        const passed = extractJson(finalAnswer) !== undefined;
        return { label: check.label, type: check.type, passed, detail: passed ? "Valid JSON object found" : "No valid JSON object found" };
      }
      if (check.type === "json_has_keys") {
        const parsed = extractJson(finalAnswer);
        const record = parsed && typeof parsed === "object" && !Array.isArray(parsed)
          ? parsed as Record<string, unknown>
          : null;
        const missing = record ? check.keys.filter((key) => !(key in record)) : check.keys;
        return {
          label: check.label,
          type: check.type,
          passed: missing.length === 0,
          detail: missing.length ? `Missing keys: ${missing.join(", ")}` : "All required keys found",
        };
      }
      if (check.type === "regex") {
        const passed = new RegExp(check.pattern, check.flags).test(finalAnswer);
        return { label: check.label, type: check.type, passed, detail: passed ? "Pattern matched" : "Pattern did not match" };
      }
      const normalize = (value: string): string => check.caseSensitive ? value : value.toLowerCase();
      const haystack = normalize(finalAnswer);
      if (check.type === "contains_all") {
        const missing = check.values.filter((value) => !haystack.includes(normalize(value)));
        return {
          label: check.label,
          type: check.type,
          passed: missing.length === 0,
          detail: missing.length ? `Missing: ${missing.join(" | ")}` : "All required values found",
        };
      }
      const found = check.values.filter((value) => haystack.includes(normalize(value)));
      return {
        label: check.label,
        type: check.type,
        passed: found.length === 0,
        detail: found.length ? `Forbidden values found: ${found.join(" | ")}` : "No forbidden values found",
      };
    } catch (error) {
      return { label: check.label, type: check.type, passed: false, detail: compactError(error) };
    }
  });
}

async function runConversation(
  task: ConversationTask,
  state: RunState,
  env: EnvLike,
  index: number,
): Promise<ConversationResult> {
  const startedAt = nowIso();
  const messages: ChatMessage[] = [{ role: "system", content: task.scenario.system }];
  const turns: TurnResult[] = [];
  for (let turnIndex = 0; turnIndex < task.scenario.turns.length; turnIndex += 1) {
    const scenarioTurn = task.scenario.turns[turnIndex];
    messages.push({ role: "user", content: scenarioTurn.user });
    const response = await streamCompletion(task.model, messages, scenarioTurn.maxTokens, env, state.timeoutMs);
    const turn: TurnResult = {
      turn_id: scenarioTurn.id,
      turn_index: turnIndex + 1,
      user_text: scenarioTurn.user,
      ok: response.ok,
      status: response.status,
      started_at: response.startedAt,
      e2e_ms: response.e2eMs,
      ttft_ms: response.ttftMs,
      ttfr_ms: response.ttfrMs,
      ttfa_ms: response.ttfaMs,
      first_delta_kind: response.firstDeltaKind,
      finish_reason: response.finishReason,
      reasoning_text: response.reasoningText,
      content_text: response.contentText,
      prompt_tokens: response.promptTokens,
      output_tokens: response.outputTokens,
      total_tokens: response.totalTokens,
      error: response.error,
    };
    turns.push(turn);
    if (!response.ok) break;
    messages.push({ role: "assistant", content: response.contentText });
  }

  const finalAnswer = [...turns].reverse().find((turn) => turn.ok)?.content_text ?? "";
  const objectiveChecks = turns.length === task.scenario.turns.length && turns.every((turn) => turn.ok)
    ? runObjectiveChecks(task.scenario.objectiveChecks, finalAnswer)
    : [];
  const judges: JudgeResult[] = [];
  if (turns.length === task.scenario.turns.length && turns.every((turn) => turn.ok)) {
    for (const judge of state.judges) {
      judges.push(await judgeConversation(judge, task.scenario, turns, objectiveChecks, env, state.timeoutMs));
    }
  }
  const requestFailures = turns.filter((turn) => !turn.ok).length;
  const totalResponseMs = sumNullable(turns.map((turn) => turn.e2e_ms));
  const inputTokens = sumNullable(turns.map((turn) => turn.prompt_tokens));
  const outputTokens = sumNullable(turns.map((turn) => turn.output_tokens));
  const totalTokens = sumNullable(turns.map((turn) => turn.total_tokens));
  return {
    conversation_id: `${state.datasetVersion}:${task.scenario.id}:${task.model.id}:${task.repeat}:${index}`,
    dataset_version: state.datasetVersion,
    scenario_id: task.scenario.id,
    scenario_title: task.scenario.title,
    category: task.scenario.category,
    model: task.model.id,
    model_label: task.model.label,
    repeat: task.repeat,
    started_at: startedAt,
    finished_at: nowIso(),
    ok: requestFailures === 0 && turns.length === task.scenario.turns.length,
    completed_turns: turns.filter((turn) => turn.ok).length,
    expected_turns: task.scenario.turns.length,
    request_failures: requestFailures,
    total_response_ms: totalResponseMs,
    input_tokens: inputTokens,
    output_tokens: outputTokens,
    total_tokens: totalTokens,
    turns,
    objective_checks: objectiveChecks,
    judges,
  };
}

function averageJudgeScore(judges: JudgeResult[]): number | null {
  const scores = judges.flatMap((judge) => judge.scores ? SCORE_FIELDS.map((field) => judge.scores![field]) : []);
  return scores.length ? scores.reduce((sum, score) => sum + score, 0) / scores.length : null;
}

export class MultiTurnBenchmarkRunner extends StatefulActor {
  async start(
    request: StartRequest,
    env: EnvLike = {},
  ): Promise<{ ok: boolean; total: number; startedAt: string; autoStart: boolean }> {
    validateRequest(request);
    const repeats = request.repeats ?? 1;
    const state: RunState = {
      datasetVersion: request.datasetVersion,
      startedAt: nowIso(),
      models: request.models,
      judges: request.judges,
      scenarios: request.scenarios,
      repeats,
      timeoutMs: request.timeoutMs ?? 900_000,
      batchSize: request.batchSize ?? 1,
      autoStart: request.autoStart ?? true,
      total: request.models.length * request.scenarios.length * repeats,
      cursor: 0,
      successes: 0,
      failures: 0,
    };
    await this.ctx.storage.deleteAll();
    await this.ctx.storage.put("state", state);
    await this.ctx.storage.put("secrets", env);
    if (state.autoStart) await this.scheduleNext(1);
    return { ok: true, total: state.total, startedAt: state.startedAt, autoStart: state.autoStart };
  }

  async status(): Promise<Record<string, unknown>> {
    const state = await this.ctx.storage.get<RunState>("state");
    if (!state) return { ok: false, error: "No run has been started" };
    return {
      ok: true,
      datasetVersion: state.datasetVersion,
      startedAt: state.startedAt,
      finishedAt: state.finishedAt ?? null,
      total: state.total,
      completed: state.cursor,
      remaining: Math.max(0, state.total - state.cursor),
      successes: state.successes,
      failures: state.failures,
      done: state.cursor >= state.total,
      autoStart: state.autoStart,
      batchSize: state.batchSize,
      lastAlarmAt: state.lastAlarmAt ?? null,
    };
  }

  async step(limit = 1, env: EnvLike = {}): Promise<Record<string, unknown>> {
    const state = await this.ctx.storage.get<RunState>("state");
    if (!state) return { ok: false, error: "No run has been started" };
    const stop = Math.min(state.total, state.cursor + Math.max(1, limit));
    let last: ConversationResult | null = null;
    for (let index = state.cursor; index < stop; index += 1) {
      last = await runConversation(taskAtIndex(state, index), state, env, index);
      await this.ctx.storage.put(resultKey(index), last);
      state.cursor = index + 1;
      if (last.ok) state.successes += 1;
      else state.failures += 1;
      await this.ctx.storage.put("state", state);
    }
    if (state.cursor >= state.total && !state.finishedAt) {
      state.finishedAt = nowIso();
      await this.ctx.storage.put("state", state);
    }
    return { ok: true, completed: state.cursor, total: state.total, done: state.cursor >= state.total, last };
  }

  async kick(): Promise<Record<string, unknown>> {
    const state = await this.ctx.storage.get<RunState>("state");
    if (!state) return { ok: false, error: "No run has been started" };
    if (state.cursor >= state.total) return { ok: true, done: true };
    await this.scheduleNext(1);
    return { ok: true, scheduled: true, completed: state.cursor, total: state.total };
  }

  async startRejudge(
    request: { onlyFailed?: boolean; judges?: ModelConfig[] } = {},
    env: EnvLike = {},
  ): Promise<Record<string, unknown>> {
    const run = await this.ctx.storage.get<RunState>("state");
    if (!run || run.cursor < run.total) {
      return { ok: false, error: "The candidate run must be complete before rejudging" };
    }
    const judges = request.judges?.length ? request.judges : run.judges;
    const tasks: RejudgeTask[] = [];
    for (let resultIndex = 0; resultIndex < run.total; resultIndex += 1) {
      const conversation = await this.ctx.storage.get<ConversationResult>(resultKey(resultIndex));
      if (!conversation) continue;
      for (let judgeIndex = 0; judgeIndex < conversation.judges.length; judgeIndex += 1) {
        const existing = conversation.judges[judgeIndex];
        if (!judges.some((judge) => judge.id === existing.judge_model)) continue;
        if (request.onlyFailed !== false && existing.ok) continue;
        tasks.push({ resultIndex, judgeIndex });
      }
    }
    const state: RejudgeState = {
      startedAt: nowIso(),
      total: tasks.length,
      cursor: 0,
      successes: 0,
      failures: 0,
      tasks,
      judges,
    };
    await this.ctx.storage.put("rejudge_state", state);
    await this.ctx.storage.put("secrets", env);
    if (tasks.length) {
      await this.scheduleNext(1);
    } else {
      state.finishedAt = nowIso();
      await this.ctx.storage.put("rejudge_state", state);
    }
    return { ok: true, total: tasks.length, startedAt: state.startedAt };
  }

  async rejudgeStatus(): Promise<Record<string, unknown>> {
    const state = await this.ctx.storage.get<RejudgeState>("rejudge_state");
    if (!state) return { ok: false, error: "No rejudge run has been started" };
    return {
      ok: true,
      startedAt: state.startedAt,
      finishedAt: state.finishedAt ?? null,
      total: state.total,
      completed: state.cursor,
      remaining: Math.max(0, state.total - state.cursor),
      successes: state.successes,
      failures: state.failures,
      done: state.cursor >= state.total,
      lastAlarmAt: state.lastAlarmAt ?? null,
    };
  }

  async rejudgeStep(limit = 1, env: EnvLike = {}): Promise<Record<string, unknown>> {
    const run = await this.ctx.storage.get<RunState>("state");
    const state = await this.ctx.storage.get<RejudgeState>("rejudge_state");
    if (!run || !state) return { ok: false, error: "No rejudge run has been started" };
    const stop = Math.min(state.total, state.cursor + Math.max(1, limit));
    for (let index = state.cursor; index < stop; index += 1) {
      const task = state.tasks[index];
      const conversation = await this.ctx.storage.get<ConversationResult>(resultKey(task.resultIndex));
      const existing = conversation?.judges[task.judgeIndex];
      const judge = existing ? state.judges.find((candidate) => candidate.id === existing.judge_model) : undefined;
      const scenario = conversation
        ? run.scenarios.find((candidate) => candidate.id === conversation.scenario_id)
        : undefined;
      if (!conversation || !existing || !judge || !scenario) {
        state.failures += 1;
        state.cursor = index + 1;
        await this.ctx.storage.put("rejudge_state", state);
        continue;
      }
      const updated = await judgeConversation(
        judge,
        scenario,
        conversation.turns,
        conversation.objective_checks,
        env,
        run.timeoutMs,
      );
      conversation.judges[task.judgeIndex] = updated;
      await this.ctx.storage.put(resultKey(task.resultIndex), conversation);
      if (updated.ok) state.successes += 1;
      else state.failures += 1;
      state.cursor = index + 1;
      await this.ctx.storage.put("rejudge_state", state);
    }
    if (state.cursor >= state.total && !state.finishedAt) {
      state.finishedAt = nowIso();
      await this.ctx.storage.put("rejudge_state", state);
    }
    return { ok: true, completed: state.cursor, total: state.total, done: state.cursor >= state.total };
  }

  async alarm(): Promise<void> {
    const state = await this.ctx.storage.get<RunState>("state");
    const secrets = (await this.ctx.storage.get<EnvLike>("secrets")) ?? {};
    if (state && state.cursor < state.total) {
      state.lastAlarmAt = nowIso();
      await this.ctx.storage.put("state", state);
      await this.step(state.batchSize, secrets);
      const updated = await this.ctx.storage.get<RunState>("state");
      if (updated && updated.autoStart && updated.cursor < updated.total) await this.scheduleNext(1);
      return;
    }
    const rejudge = await this.ctx.storage.get<RejudgeState>("rejudge_state");
    if (!rejudge || rejudge.cursor >= rejudge.total) return;
    rejudge.lastAlarmAt = nowIso();
    await this.ctx.storage.put("rejudge_state", rejudge);
    await this.rejudgeStep(1, secrets);
    const updated = await this.ctx.storage.get<RejudgeState>("rejudge_state");
    if (updated && updated.cursor < updated.total) await this.scheduleNext(1);
  }

  async results(): Promise<{ state: RunState | null; conversations: ConversationResult[] }> {
    const state = (await this.ctx.storage.get<RunState>("state")) ?? null;
    const stored = await this.ctx.storage.list<ConversationResult>({ prefix: "result:", limit: 1000 });
    return { state, conversations: [...stored.values()] };
  }

  async conversationsCsv(): Promise<string> {
    const { conversations } = await this.results();
    const fields = [
      "conversation_id", "dataset_version", "scenario_id", "scenario_title", "category", "model", "model_label",
      "repeat", "started_at", "finished_at", "ok", "completed_turns", "expected_turns", "request_failures",
      "total_response_ms", "input_tokens", "output_tokens", "total_tokens", "objective_checks_passed",
      "objective_checks_total", "judge_completion_votes", "judge_results", "average_judge_score",
    ];
    const rows = conversations.map((conversation) => {
      const record: Record<string, unknown> = {
        ...conversation,
        objective_checks_passed: conversation.objective_checks.filter((check) => check.passed).length,
        objective_checks_total: conversation.objective_checks.length,
        judge_completion_votes: conversation.judges.filter((judge) => judge.completed === true).length,
        judge_results: conversation.judges.filter((judge) => judge.ok).length,
        average_judge_score: averageJudgeScore(conversation.judges),
      };
      return fields.map((field) => csvEscape(record[field])).join(",");
    });
    return [fields.join(","), ...rows].join("\n");
  }

  async turnsCsv(): Promise<string> {
    const { conversations } = await this.results();
    const fields = [
      "conversation_id", "dataset_version", "scenario_id", "category", "model", "model_label", "repeat",
      "turn_id", "turn_index", "user_text", "ok", "status", "started_at", "e2e_ms", "ttft_ms", "ttfr_ms",
      "ttfa_ms", "first_delta_kind", "reasoning_text", "content_text", "prompt_tokens", "output_tokens",
      "total_tokens", "finish_reason", "error",
    ];
    const rows: string[] = [];
    for (const conversation of conversations) {
      for (const turn of conversation.turns) {
        const record: Record<string, unknown> = { ...conversation, ...turn };
        rows.push(fields.map((field) => csvEscape(record[field])).join(","));
      }
    }
    return [fields.join(","), ...rows].join("\n");
  }

  async judgesCsv(): Promise<string> {
    const { conversations } = await this.results();
    const fields = [
      "conversation_id", "dataset_version", "scenario_id", "category", "model", "model_label", "repeat",
      "judge_model", "judge_label", "ok", "status", "finish_reason", "completed", ...SCORE_FIELDS, "summary", "strengths",
      "issues", "raw_response", "error",
    ];
    const rows: string[] = [];
    for (const conversation of conversations) {
      for (const judge of conversation.judges) {
        const record: Record<string, unknown> = {
          ...conversation,
          ...judge,
          ...(judge.scores ?? {}),
          strengths: judge.strengths.join(" | "),
          issues: judge.issues.join(" | "),
        };
        rows.push(fields.map((field) => csvEscape(record[field])).join(","));
      }
    }
    return [fields.join(","), ...rows].join("\n");
  }

  async objectiveChecksCsv(): Promise<string> {
    const { conversations } = await this.results();
    const fields = [
      "conversation_id", "dataset_version", "scenario_id", "category", "model", "model_label", "repeat",
      "label", "type", "passed", "detail",
    ];
    const rows: string[] = [];
    for (const conversation of conversations) {
      for (const check of conversation.objective_checks) {
        const record: Record<string, unknown> = { ...conversation, ...check };
        rows.push(fields.map((field) => csvEscape(record[field])).join(","));
      }
    }
    return [fields.join(","), ...rows].join("\n");
  }

  private async scheduleNext(delayMs: number): Promise<void> {
    await this.ctx.storage.setAlarm(Date.now() + delayMs);
  }
}
