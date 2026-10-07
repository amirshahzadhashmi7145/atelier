"use client";

import type { Snapshot, Task } from "@/lib/types";

export const RUN_STEPS = [
  { id: "claim", label: "Claim", hint: "Zone agent picks up the task" },
  { id: "implement", label: "Implement", hint: "Writes only inside its ownership zone" },
  { id: "checks", label: "Checks", hint: "Sandbox unit / integration / ui" },
  { id: "staff", label: "Staff", hint: "Full-stack review + evidence gate" },
  { id: "qa", label: "QA", hint: "Acceptance criteria judged" },
  { id: "gate", label: "Gate", hint: "Merge wait or automatic accept" },
] as const;

export type RunStepId = (typeof RUN_STEPS)[number]["id"];

type StepStatus = "done" | "active" | "pending" | "failed";

export function deriveRunProgress(snapshot: Snapshot, busy: boolean) {
  const active =
    snapshot.tasks.find((task) => task.state === "in_progress") ??
    snapshot.tasks.find((task) => task.state === "in_review") ??
    snapshot.tasks.find((task) => task.state === "gated") ??
    null;

  if (!active && !busy) {
    return null;
  }

  const taskEvents = active
    ? snapshot.events.filter((event) => {
        const key = event.payload?.key;
        return typeof key === "string" && key === active.key;
      })
    : [];

  const types = new Set(taskEvents.map((event) => event.type));
  const taskRuns = active
    ? snapshot.runs.filter((run) => run.task_id === active.id)
    : [];
  const hasImplement = taskRuns.some((run) => run.purpose === "implement");
  const hasChecks = snapshot.checks.some((check) => check.task_id === active?.id);
  const staffFailed = types.has("staff.failed");
  const qaFailed = types.has("qa.failed") || types.has("qa.rejected_untestable");
  const taskFailed = types.has("task.failed");

  let currentIndex = 0;
  if (!active && busy) {
    currentIndex = 0;
  } else if (active?.state === "in_progress") {
    if (hasChecks) currentIndex = 2;
    else if (hasImplement) currentIndex = 1;
    else currentIndex = 0;
  } else if (active?.state === "in_review") {
    if (types.has("staff.passed") || types.has("qa.untestable") || types.has("qa.passed")) {
      currentIndex = types.has("qa.untestable") || types.has("qa.passed") ? 4 : 3;
    } else if (staffFailed) {
      currentIndex = 3;
    } else {
      currentIndex = 3;
    }
  } else if (active?.state === "gated" || active?.state === "done") {
    currentIndex = 5;
  }

  if (taskFailed && active?.state === "ready") {
    currentIndex = hasChecks ? 2 : hasImplement ? 1 : 0;
  }

  const statuses: StepStatus[] = RUN_STEPS.map((step, index) => {
    if (staffFailed && step.id === "staff") return "failed";
    if (qaFailed && step.id === "qa") return "failed";
    if (taskFailed && index === currentIndex && active?.state === "ready") return "failed";
    if (index < currentIndex) return "done";
    if (index === currentIndex) return busy || active?.state === "in_progress" || active?.state === "in_review" ? "active" : "done";
    return "pending";
  });

  // Gate step is done when gated/done; active while waiting on merge.
  if (active?.state === "gated") {
    statuses[5] = "active";
  }
  if (active?.state === "done") {
    statuses[5] = "done";
  }

  const doneCount = statuses.filter((status) => status === "done").length;
  const failed = statuses.some((status) => status === "failed");
  const pct = Math.round(((doneCount + (statuses[currentIndex] === "active" ? 0.45 : 0)) / RUN_STEPS.length) * 100);

  return {
    task: active,
    currentIndex,
    statuses,
    pct: Math.min(100, Math.max(busy && !active ? 8 : 0, pct)),
    failed,
    live: Boolean(busy || active?.state === "in_progress" || active?.state === "in_review"),
  };
}

export function RunPipeline({
  snapshot,
  busy,
}: {
  snapshot: Snapshot;
  busy: boolean;
}) {
  const progress = deriveRunProgress(snapshot, busy);
  if (!progress) return null;

  const { task, statuses, pct, failed, live } = progress;
  const activeLabel = RUN_STEPS[progress.currentIndex]?.label ?? "Run";

  return (
    <div className="run-pipeline border border-line bg-gradient-to-br from-white/90 to-[#f7f2e8]/90 p-5 shadow-[0_18px_40px_-32px_rgba(28,25,21,0.55)]">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs tracking-[0.2em] text-muted uppercase">
            {live ? "Live run" : failed ? "Run stopped" : "Last run"}
          </p>
          <h3 className="font-serif mt-1 text-2xl">
            {task ? `${task.key} · ${activeLabel}` : "Starting next ready task"}
          </h3>
          <p className="mt-1 text-sm text-muted">
            {task
              ? `${task.title} · ${task.zone.replaceAll("_", " ")}`
              : "Claiming a ready task from the queue…"}
          </p>
        </div>
        <p className={`text-sm tabular-nums ${failed ? "text-oxide" : "text-ink"}`}>
          {pct}%
        </p>
      </div>

      <div
        className="run-pipeline-track mt-4 h-2 overflow-hidden bg-line/80"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        aria-label="Task run progress"
      >
        <div
          className={`h-full transition-[width] duration-500 ease-out ${
            failed ? "bg-oxide" : live ? "run-pipeline-fill" : "bg-moss"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <ol className="mt-5 grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
        {RUN_STEPS.map((step, index) => {
          const status = statuses[index];
          return (
            <li
              key={step.id}
              className={`rounded-sm border px-2.5 py-2 ${
                status === "active"
                  ? "border-ink bg-ink text-paper"
                  : status === "done"
                    ? "border-moss/40 bg-moss-soft text-ink"
                    : status === "failed"
                      ? "border-oxide bg-oxide-soft text-oxide"
                      : "border-line/80 bg-paper/40 text-muted"
              }`}
            >
              <p className="text-[10px] tracking-[0.16em] uppercase opacity-80">
                {status === "done" ? "Done" : status === "active" ? "Now" : status === "failed" ? "Fail" : "Next"}
              </p>
              <p className="mt-0.5 text-sm font-medium">{step.label}</p>
              <p className={`mt-0.5 text-[11px] leading-snug ${status === "active" ? "text-paper/75" : "opacity-80"}`}>
                {step.hint}
              </p>
            </li>
          );
        })}
      </ol>

      {task ? <TaskMiniMeter task={task} /> : null}
    </div>
  );
}

function TaskMiniMeter({ task }: { task: Task }) {
  const retries = `${task.retry_count}/${task.max_retries}`;
  return (
    <p className="mt-4 text-xs text-muted">
      Retries {retries}
      {task.branch_name ? ` · ${task.branch_name}` : ""}
      {task.estimate_tokens ? ` · est. ${task.estimate_tokens.toLocaleString()} tokens` : ""}
    </p>
  );
}

export function StageProgress({
  stages,
  current,
}: {
  stages: { label: string; hint: string }[];
  current: number;
}) {
  const pct = stages.length <= 1 ? 0 : Math.round((Math.max(0, current) / (stages.length - 1)) * 100);
  return (
    <div className="space-y-4">
      <div className="run-pipeline-track h-1.5 overflow-hidden bg-line/70">
        <div className="h-full bg-ink transition-[width] duration-500" style={{ width: `${pct}%` }} />
      </div>
      <ol className="space-y-4">
        {stages.map((step, index) => {
          const state = index < current ? "done" : index === current ? "now" : "later";
          return (
            <li key={step.label} className={state === "later" ? "text-muted" : "text-ink"}>
              <p className="text-xs tracking-widest uppercase">
                {state === "done" ? "Done" : state === "now" ? "Now" : "Later"}
              </p>
              <p className="font-serif text-xl">{step.label}</p>
              <p className="text-sm text-muted">{step.hint}</p>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
