import { StatefulActor } from "@telnyx/edge-runtime";

export class BenchmarkRunner extends StatefulActor {
  async status(): Promise<Record<string, unknown>> {
    return { ok: true, canary: true };
  }
}
