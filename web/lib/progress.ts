/** Planning rail stages → progress through the Atelier pipeline. */
export const PLAN_STEPS = [
  { label: "Intake", match: (stage: string) => stage === "intake" },
  {
    label: "Clarify",
    match: (stage: string) => stage === "clarifying" || stage === "interpreted",
  },
  {
    label: "Requirements",
    match: (stage: string) => stage.startsWith("requirements"),
  },
  {
    label: "Architecture",
    match: (stage: string) => stage.startsWith("architecture"),
  },
  { label: "Tasks", match: (stage: string) => stage === "tasks_ready" },
] as const;

export function planStepIndex(stage: string): number {
  const index = PLAN_STEPS.findIndex((step) => step.match(stage));
  return index < 0 ? 0 : index;
}

export function planProgressPct(stage: string): number {
  const index = planStepIndex(stage);
  if (stage === "tasks_ready") return 100;
  return Math.round(((index + 0.35) / PLAN_STEPS.length) * 100);
}

export function taskProgress(counts: Record<string, number>): {
  done: number;
  total: number;
  active: number;
  pct: number;
} {
  const done = (counts.done ?? 0) + (counts.merged ?? 0);
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);
  const active =
    (counts.in_progress ?? 0) +
    (counts.in_review ?? 0) +
    (counts.ready ?? 0) +
    (counts.blocked ?? 0) +
    (counts.escalated ?? 0) +
    (counts.gated ?? 0);
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  return { done, total, active, pct };
}

export function spendProgress(tokens: number, ceiling: number): number {
  if (ceiling <= 0) return 0;
  return Math.min(100, Math.round((tokens / ceiling) * 100));
}
