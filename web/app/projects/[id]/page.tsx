"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, loadProject, loadTaskDetail } from "@/lib/api";
import type { Requirement, Snapshot, TaskDetail } from "@/lib/types";

const RAIL = [
  { label: "Intake", hint: "The request, in your words", match: (stage: string) => stage === "intake" },
  {
    label: "Clarify",
    hint: "Questions, then recorded assumptions",
    match: (stage: string) => stage === "clarifying" || stage === "interpreted",
  },
  {
    label: "Requirements",
    hint: "Behaviour a test can fail",
    match: (stage: string) => stage.startsWith("requirements"),
  },
  {
    label: "Architecture",
    hint: "Decisions and who owns which files",
    match: (stage: string) => stage.startsWith("architecture"),
  },
  { label: "Tasks", hint: "Work, and what it waits on", match: (stage: string) => stage === "tasks_ready" },
];

const GATE_LABELS: { key: string; label: string; irreversible?: boolean }[] = [
  { key: "requirements", label: "Requirements" },
  { key: "architecture", label: "Architecture" },
  { key: "merge", label: "Merge", irreversible: true },
  { key: "deployment", label: "Deployment", irreversible: true },
  { key: "external_side_effects", label: "External effects", irreversible: true },
  { key: "spend_increase", label: "Spend increase" },
];

const POLL_MS = 1500;

function syncLabel(syncedAt: number | null) {
  if (!syncedAt) return "connecting…";
  const ms = Date.now() - syncedAt;
  if (ms < 2000) return "live";
  if (ms < 60000) return `updated ${Math.floor(ms / 1000)}s ago`;
  return `updated ${Math.floor(ms / 60000)}m ago`;
}

export default function ProjectPage() {
  const params = useParams<{ id: string }>();
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [editingInterpretation, setEditingInterpretation] = useState(false);
  const [interpretation, setInterpretation] = useState("");
  const [editingRequirement, setEditingRequirement] = useState<string | null>(null);
  const [ceilingInput, setCeilingInput] = useState("");
  const [gateAck, setGateAck] = useState("");
  const [openTaskId, setOpenTaskId] = useState<string | null>(null);
  const [taskDetail, setTaskDetail] = useState<TaskDetail | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);
  const [amendPath, setAmendPath] = useState("");
  const [amendContent, setAmendContent] = useState("");
  const [amendSummary, setAmendSummary] = useState("");
  const [resumeAnswers, setResumeAnswers] = useState<Record<string, string>>({});
  const [syncedAt, setSyncedAt] = useState<number | null>(null);
  const [clock, setClock] = useState(() => Date.now());
  const openTaskIdRef = useRef<string | null>(null);
  openTaskIdRef.current = openTaskId;

  async function refresh() {
    const next = await loadProject(params.id);
    setSnapshot(next);
    setSyncedAt(Date.now());
    return next;
  }

  // FR-UI-6: keep status live even while a long Run is in flight.
  useEffect(() => {
    let cancelled = false;
    let inFlight = false;

    const tick = async () => {
      if (cancelled || document.hidden || inFlight) return;
      inFlight = true;
      try {
        const next = await loadProject(params.id);
        if (cancelled) return;
        setSnapshot(next);
        setSyncedAt(Date.now());
        const openId = openTaskIdRef.current;
        if (openId) {
          try {
            const detail = await loadTaskDetail(params.id, openId);
            if (!cancelled && openTaskIdRef.current === openId) {
              setTaskDetail(detail);
            }
          } catch {
            // Keep the last task drill-down; the next tick retries.
          }
        }
      } catch {
        // Keep the last good snapshot; the next tick retries.
      } finally {
        inFlight = false;
      }
    };

    tick();
    const poll = window.setInterval(tick, POLL_MS);
    const clockTimer = window.setInterval(() => setClock(Date.now()), 1000);
    const onVisible = () => {
      if (!document.hidden) void tick();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelled = true;
      window.clearInterval(poll);
      window.clearInterval(clockTimer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [params.id]);

  async function inspectTask(taskId: string) {
    if (openTaskId === taskId) {
      setOpenTaskId(null);
      setTaskDetail(null);
      return;
    }
    setDetailBusy(true);
    setError("");
    try {
      const detail = await loadTaskDetail(params.id, taskId);
      setOpenTaskId(taskId);
      setTaskDetail(detail);
      setAmendPath("");
      setAmendContent("");
      setAmendSummary("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load that task.");
    } finally {
      setDetailBusy(false);
    }
  }

  async function amendBranch(taskId: string) {
    setBusy(true);
    setError("");
    try {
      const detail = await api<TaskDetail>(`/api/projects/${params.id}/tasks/${taskId}/amend`, {
        method: "POST",
        body: JSON.stringify({
          path: amendPath,
          content: amendContent,
          summary: amendSummary.trim() || "Person amended the branch.",
        }),
      });
      setTaskDetail(detail);
      setAmendPath("");
      setAmendContent("");
      setAmendSummary("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The branch could not be amended.");
    } finally {
      setBusy(false);
    }
  }

  async function run(action: () => Promise<Snapshot>): Promise<Snapshot | null> {
    setBusy(true);
    setError("");
    try {
      const next = await action();
      setSnapshot(next);
      setSyncedAt(Date.now());
      return next;
    } catch (err) {
      setError(err instanceof Error ? err.message : "That step failed.");
      try {
        setSnapshot(await loadProject(params.id));
        setSyncedAt(Date.now());
      } catch {
        // The error above is the one to show.
      }
      return null;
    } finally {
      setBusy(false);
    }
  }

  if (!snapshot) {
    return <main className="mx-auto max-w-5xl px-6 py-16">{error || "Loading the project…"}</main>;
  }

  const { project } = snapshot;
  const can = (action: string) => project.next_actions.includes(action);
  const current = RAIL.findIndex((step) => step.match(project.stage));
  const usingFake = snapshot.runs.some((run) => run.provider === "fake");
  const spendTokens = project.spend_tokens ?? 0;
  const spendCeiling = project.spend_ceiling_tokens ?? 0;
  const spendAlerts = project.spend_alerts ?? [];
  const highestAlert = spendAlerts.length ? Math.max(...spendAlerts) : 0;
  const spendByRole = project.spend_by_role ?? [];
  const spendByTask = project.spend_by_task ?? [];
  const estimateTokens = project.estimate_tokens ?? 0;
  const spendOverEstimate = Boolean(project.spend_over_estimate);
  const gatePolicy = project.gate_policy ?? {};
  const status = project.status ?? {
    task_counts: {},
    blocked: [],
    open_gates: [],
    agents: [],
    needs_you: [],
  };
  // Touch clock so the sync label re-renders every second.
  void clock;
  const liveLabel = syncLabel(syncedAt);

  return (
    <main className="mx-auto grid max-w-6xl gap-10 px-6 py-10 lg:grid-cols-[14rem_1fr]">
      <aside>
        <Link href="/" className="text-xs tracking-[0.22em] text-oxide uppercase">
          Atelier
        </Link>
        <Link
          href={`/office?project=${project.id}`}
          className="mt-3 block text-sm text-muted underline-offset-4 hover:text-ink hover:underline"
        >
          Coders Alley
        </Link>
        <ol className="mt-8 space-y-5">
          {RAIL.map((step, index) => (
            <li key={step.label} className={index === current ? "text-ink" : "text-muted"}>
              <p className="text-xs tracking-widest uppercase">{index < current ? "Done" : index === current ? "Now" : "Later"}</p>
              <p className="font-serif text-xl">{step.label}</p>
              <p className="text-sm">{step.hint}</p>
            </li>
          ))}
        </ol>
      </aside>

      <div className="space-y-8">
        <header>
          <h1 className="font-serif text-4xl">{project.name}</h1>
          <p className="mt-2 max-w-2xl text-muted">{project.description}</p>
          {project.tech_preferences ? (
            <p className="mt-2 text-sm text-muted">Preferences: {project.tech_preferences}</p>
          ) : null}
          {project.github_repo ? (
            <p className="mt-2 text-sm text-muted">
              GitHub:{" "}
              <a
                className="underline"
                href={`https://github.com/${project.github_repo}`}
                target="_blank"
                rel="noreferrer"
              >
                {project.github_repo}
              </a>
            </p>
          ) : (
            <div className="mt-3">
              <button
                type="button"
                disabled={busy}
                className="border border-ink px-3 py-2 text-sm"
                onClick={() =>
                  run(() =>
                    api(`/api/projects/${project.id}/github-repo`, {
                      method: "POST",
                      body: JSON.stringify({ create: true, private: false }),
                    }),
                  )
                }
              >
                Create GitHub repository
              </button>
              <p className="mt-1 text-sm text-muted">
                No remote yet — creates a public repo from the project name using GITHUB_TOKEN.
              </p>
            </div>
          )}
          <p className="mt-2 text-sm text-muted">
            Spend: {spendTokens.toLocaleString()} / {spendCeiling.toLocaleString()} tokens
            {estimateTokens
              ? ` · plan estimate ${estimateTokens.toLocaleString()}`
              : ""}
            {highestAlert ? ` · alerted at ${spendAlerts.map((n) => `${n}%`).join(", ")}` : ""}
          </p>
          {spendByRole.length ? (
            <p className="mt-1 text-sm text-muted">
              By role:{" "}
              {spendByRole.map((item) => `${item.role} ${item.tokens.toLocaleString()}`).join(" · ")}
            </p>
          ) : null}
          {spendByTask.length ? (
            <p className="mt-1 text-sm text-muted">
              By task:{" "}
              {spendByTask.map((item) => `${item.task_key} ${item.tokens.toLocaleString()}`).join(" · ")}
            </p>
          ) : null}
          <div className="mt-4 flex flex-wrap items-end gap-3">
            {can("pause") ? (
              <button
                type="button"
                disabled={busy}
                className="border border-ink px-3 py-2 text-sm"
                onClick={() => run(() => api(`/api/projects/${project.id}/pause`, { method: "POST" }))}
              >
                Pause project
              </button>
            ) : null}
            {can("unpause") ? (
              <button
                type="button"
                disabled={busy}
                className="bg-moss px-3 py-2 text-sm text-white"
                onClick={() => run(() => api(`/api/projects/${project.id}/unpause`, { method: "POST" }))}
              >
                Unpause project
              </button>
            ) : null}
            {can("revoke_agents") ? (
              <button
                type="button"
                disabled={busy}
                className="border border-oxide px-3 py-2 text-sm text-oxide"
                onClick={() => run(() => api(`/api/projects/${project.id}/revoke-agents`, { method: "POST" }))}
              >
                Revoke agents
              </button>
            ) : null}
            {can("restore_agents") ? (
              <button
                type="button"
                disabled={busy}
                className="bg-moss px-3 py-2 text-sm text-white"
                onClick={() => run(() => api(`/api/projects/${project.id}/restore-agents`, { method: "POST" }))}
              >
                Restore agents
              </button>
            ) : null}
            <label className="text-sm">
              Raise ceiling
              <span className="mt-1 flex gap-2">
                <input
                  type="number"
                  min={spendTokens || 1}
                  value={ceilingInput}
                  onChange={(event) => setCeilingInput(event.target.value)}
                  placeholder={String(spendCeiling || "")}
                  className="w-40 border border-line bg-paper px-3 py-2"
                />
                <button
                  type="button"
                  disabled={busy || !ceilingInput}
                  className="border border-ink px-3 py-2 text-sm"
                  onClick={() =>
                    run(() =>
                      api(`/api/projects/${project.id}/spend-ceiling`, {
                        method: "POST",
                        body: JSON.stringify({ spend_ceiling_tokens: Number(ceilingInput) }),
                      }),
                    ).then((next) => {
                      setCeilingInput("");
                      return next;
                    })
                  }
                >
                  Save
                </button>
              </span>
            </label>
          </div>
        </header>

        {project.paused ? (
          <p className="border border-oxide bg-oxide-soft px-4 py-3 text-sm">
            This project is paused. Planning and task runs will not continue until you unpause it
            {spendCeiling > 0 && spendTokens >= spendCeiling
              ? " and raise the spend ceiling if it was hit"
              : ""}
            .
          </p>
        ) : null}

        {!project.paused && project.agents_revoked ? (
          <p className="border border-oxide bg-oxide-soft px-4 py-3 text-sm">
            Agent authority is revoked. You can still approve gates, amend branches, and edit the plan.
            Restore agents when they should act again.
          </p>
        ) : null}

        {!project.paused && highestAlert >= 80 ? (
          <p className="border border-oxide bg-oxide-soft px-4 py-3 text-sm">
            Spend has crossed {highestAlert}% of the ceiling ({spendTokens.toLocaleString()} of{" "}
            {spendCeiling.toLocaleString()} tokens). Raise the ceiling before the project is paused.
          </p>
        ) : null}

        {spendOverEstimate ? (
          <p className="border border-oxide bg-oxide-soft px-4 py-3 text-sm">
            Actual spend ({spendTokens.toLocaleString()} tokens) has diverged past the plan estimate (
            {estimateTokens.toLocaleString()} tokens).
          </p>
        ) : null}

        {usingFake ? (
          <p className="border border-line bg-oxide-soft px-4 py-3 text-sm">
            This plan is coming from the local stand-in, not a model. The gates and the validators are
            real. Set <code>LLM_PROVIDER=openai</code> and an API key when you want a model to write the plan.
          </p>
        ) : null}
        {error ? <p className="text-sm text-oxide">{error}</p> : null}

        <section className="border border-line bg-white/70 p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="font-serif text-2xl">Status</h2>
            <p className="text-xs tracking-[0.18em] text-muted uppercase">{liveLabel}</p>
          </div>
          <p className="mt-1 text-sm text-muted">
            Task counts, who is waiting on whom, open gates, and which agents are busy. Refreshes every
            1.5s while this page is open — including during a long Run.
          </p>
          {status.needs_you.length ? (
            <p className="mt-4 border border-oxide bg-oxide-soft px-4 py-3 text-sm">
              Waiting on you: {status.needs_you.join(" · ")}. Resume below, or run other ready tasks.
            </p>
          ) : null}
          {Object.keys(status.task_counts).length ? (
            <p className="mt-4 text-sm">
              Tasks:{" "}
              {Object.entries(status.task_counts)
                .map(([state, count]) => `${state.replaceAll("_", " ")} ${count}`)
                .join(" · ")}
            </p>
          ) : (
            <p className="mt-4 text-sm text-muted">No tasks yet.</p>
          )}
          {status.blocked.length ? (
            <ul className="mt-3 space-y-1 text-sm text-muted">
              {status.blocked.map((item) => (
                <li key={item.task_key}>
                  {item.task_key} blocked by {item.blocked_by.join(", ") || "unfinished work"}
                </li>
              ))}
            </ul>
          ) : null}
          {status.open_gates.length ? (
            <p className="mt-3 text-sm text-muted">Open gates: {status.open_gates.join(" · ")}</p>
          ) : null}
          {status.agents.length ? (
            <p className="mt-3 text-sm">
              Agents:{" "}
              {status.agents.map((agent) => `${agent.role} ${agent.state}`).join(" · ")}
            </p>
          ) : null}
        </section>

        <section className="border border-line bg-white/70 p-5">
          <h2 className="font-serif text-2xl">Approval policy</h2>
          <p className="mt-1 text-sm text-muted">
            Each gate is human or automatic. Merge, deployment, and external effects need a written
            acknowledgement before they can run without a person.
          </p>
          <label className="mt-4 block text-sm">
            Acknowledgement for irreversible automation
            <input
              type="text"
              value={gateAck}
              onChange={(event) => setGateAck(event.target.value)}
              placeholder="I accept unattended merges for this project."
              className="mt-1 w-full border border-line bg-paper px-3 py-2"
            />
          </label>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {GATE_LABELS.map((gate) => (
              <li key={gate.key} className="flex items-center justify-between gap-3 text-sm">
                <span>
                  {gate.label}
                  {gate.irreversible ? <span className="text-muted"> · irreversible</span> : null}
                </span>
                <select
                  disabled={busy || project.paused}
                  value={gatePolicy[gate.key] ?? "human"}
                  className="border border-line bg-paper px-2 py-1"
                  onChange={(event) => {
                    const nextMode = event.target.value;
                    const needsAck =
                      gate.irreversible &&
                      nextMode === "automatic" &&
                      (gatePolicy[gate.key] ?? "human") !== "automatic";
                    if (needsAck && !gateAck.trim()) {
                      setError(
                        `Write an acknowledgement before setting ${gate.label.toLowerCase()} to automatic.`,
                      );
                      return;
                    }
                    void run(() =>
                      api(`/api/projects/${project.id}/gate-policy`, {
                        method: "POST",
                        body: JSON.stringify({
                          gate_policy: { ...gatePolicy, [gate.key]: nextMode },
                          acknowledgement: needsAck ? gateAck.trim() : undefined,
                        }),
                      }),
                    ).then((next) => {
                      if (next && needsAck) setGateAck("");
                    });
                  }}
                >
                  <option value="human">Human</option>
                  <option value="automatic">Automatic</option>
                </select>
              </li>
            ))}
          </ul>
        </section>

        <section className="border border-line bg-white/70 p-5">
          <h2 className="font-serif text-2xl">Interpretation</h2>
          <p className="mt-1 text-sm text-muted">The agent restates the request before anyone writes requirements. You can correct it.</p>
          {project.interpretation ? (
            editingInterpretation ? (
              <div className="mt-4 space-y-3">
                <textarea
                  value={interpretation}
                  onChange={(event) => setInterpretation(event.target.value)}
                  rows={6}
                  className="w-full border border-line bg-paper px-3 py-2"
                />
                <button
                  type="button"
                  disabled={busy || !can("edit_interpretation")}
                  className="bg-ink px-3 py-2 text-sm text-paper"
                  onClick={() =>
                    run(() =>
                      api(`/api/projects/${project.id}/interpretation`, {
                        method: "PATCH",
                        body: JSON.stringify({ interpretation }),
                      }),
                    ).then((next) => {
                      setEditingInterpretation(false);
                      return next;
                    })
                  }
                >
                  Save correction
                </button>
              </div>
            ) : (
              <>
                <p className="mt-4 whitespace-pre-wrap leading-relaxed">{project.interpretation}</p>
                {can("edit_interpretation") ? (
                  <button
                    type="button"
                    className="mt-3 text-sm underline"
                    onClick={() => {
                      setInterpretation(project.interpretation ?? "");
                      setEditingInterpretation(true);
                    }}
                  >
                    Correct this
                  </button>
                ) : null}
              </>
            )
          ) : (
            <button
              type="button"
              disabled={busy || !can("interpret")}
              className="mt-4 bg-ink px-3 py-2 text-sm text-paper"
              onClick={() => run(() => api(`/api/projects/${project.id}/interpret`, { method: "POST" }))}
            >
              {busy ? "Working…" : "Interpret the request"}
            </button>
          )}
        </section>

        {snapshot.clarifications.length > 0 ? (
          <section className="border border-line bg-white/70 p-5">
            <h2 className="font-serif text-2xl">Clarifications</h2>
            <p className="mt-1 text-sm text-muted">
              At most {project.max_questions} questions a round, and {project.max_rounds} rounds. After that the
              agent records assumptions and moves on. Round {project.clarification_round}.
            </p>
            <ul className="mt-4 space-y-4">
              {snapshot.clarifications.map((item) => (
                <li key={item.id}>
                  <p>{item.question}</p>
                  <p className="text-sm text-muted">Settles: {item.resolves}</p>
                  {item.status === "open" ? (
                    <textarea
                      value={answers[item.id] ?? ""}
                      onChange={(event) => setAnswers({ ...answers, [item.id]: event.target.value })}
                      rows={2}
                      className="mt-2 w-full border border-line bg-paper px-3 py-2"
                    />
                  ) : (
                    <p className="mt-1 text-sm">
                      {item.status === "answered" ? item.answer : "Left unanswered. An assumption was recorded."}
                    </p>
                  )}
                </li>
              ))}
            </ul>
            {can("answer_clarifications") ? (
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={busy}
                  className="bg-ink px-3 py-2 text-sm text-paper"
                  onClick={() =>
                    run(() =>
                      api(`/api/projects/${project.id}/clarifications`, {
                        method: "POST",
                        body: JSON.stringify({
                          proceed: false,
                          answers: snapshot.clarifications
                            .filter((item) => item.status === "open")
                            .map((item) => ({ id: item.id, answer: answers[item.id] ?? "" })),
                        }),
                      }),
                    )
                  }
                >
                  Save answers
                </button>
                <button
                  type="button"
                  disabled={busy}
                  className="border border-ink px-3 py-2 text-sm"
                  onClick={() =>
                    run(() =>
                      api(`/api/projects/${project.id}/clarifications`, {
                        method: "POST",
                        body: JSON.stringify({
                          proceed: true,
                          answers: snapshot.clarifications
                            .filter((item) => item.status === "open")
                            .map((item) => ({ id: item.id, answer: answers[item.id] ?? "" })),
                        }),
                      }),
                    )
                  }
                >
                  Proceed on assumptions
                </button>
              </div>
            ) : null}
          </section>
        ) : null}

        {snapshot.assumptions.length > 0 ? (
          <section className="border border-line bg-oxide-soft p-5">
            <h2 className="font-serif text-2xl">Assumptions</h2>
            <p className="mt-1 text-sm">These are visible on purpose. A wrong assumption can be corrected. A stalled project cannot.</p>
            <ul className="mt-3 list-disc space-y-1 pl-5">
              {snapshot.assumptions.map((item) => (
                <li key={item.id}>{item.statement}</li>
              ))}
            </ul>
          </section>
        ) : null}

        {can("generate_requirements") || snapshot.requirements.length > 0 ? (
          <section className="border border-line bg-white/70 p-5">
            <h2 className="font-serif text-2xl">Requirements</h2>
            <p className="mt-1 text-sm text-muted">
              Every functional requirement needs an acceptance criterion. Approval is a gate: the architecture
              cannot start without it.
            </p>
            {can("generate_requirements") || can("rewrite_requirements") ? (
              <button
                type="button"
                disabled={busy}
                className="mt-4 bg-ink px-3 py-2 text-sm text-paper"
                onClick={() => run(() => api(`/api/projects/${project.id}/requirements`, { method: "POST" }))}
              >
                {snapshot.requirements.length ? "Rewrite requirements" : "Write requirements"}
              </button>
            ) : null}
            {snapshot.stories.length > 0 ? (
              <ul className="mt-4 space-y-1 text-sm">
                {snapshot.stories.map((story) => (
                  <li key={story.id}>{story.statement}</li>
                ))}
              </ul>
            ) : null}
            <ul className="mt-4 space-y-4">
              {snapshot.requirements.map((requirement) => (
                <li key={requirement.id} className="border-t border-line pt-4">
                  {editingRequirement === requirement.id ? (
                    <RequirementForm
                      initial={requirement}
                      busy={busy}
                      onCancel={() => setEditingRequirement(null)}
                      onSave={(body) =>
                        run(() =>
                          api(`/api/projects/${project.id}/requirements/${requirement.id}`, {
                            method: "PATCH",
                            body: JSON.stringify(body),
                          }),
                        ).then((next) => {
                          setEditingRequirement(null);
                          return next;
                        })
                      }
                    />
                  ) : (
                    <>
                      <p className="text-xs tracking-widest text-muted uppercase">
                        {requirement.key} · {requirement.kind.replaceAll("_", " ")}
                      </p>
                      <h3 className="font-serif text-xl">{requirement.title}</h3>
                      <p className="mt-1">{requirement.statement}</p>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                        {requirement.criteria.map((criterion) => (
                          <li key={criterion.id}>
                            <span className="text-muted">{criterion.key}. </span>
                            {criterion.statement}
                          </li>
                        ))}
                      </ul>
                      {can("edit_requirements") ? (
                        <div className="mt-2 flex gap-3 text-sm">
                          <button type="button" className="underline" onClick={() => setEditingRequirement(requirement.id)}>
                            Edit
                          </button>
                          <button
                            type="button"
                            className="underline"
                            onClick={() =>
                              run(() =>
                                api(`/api/projects/${project.id}/requirements/${requirement.id}`, { method: "DELETE" }),
                              )
                            }
                          >
                            Remove
                          </button>
                        </div>
                      ) : null}
                    </>
                  )}
                </li>
              ))}
            </ul>
            {can("approve_requirements") ? (
              <div className="mt-4">
                <GateButtons
                  busy={busy}
                  gate="requirements"
                  onDecide={(decision) =>
                    run(() =>
                      api(`/api/projects/${project.id}/gates`, {
                        method: "POST",
                        body: JSON.stringify({ gate: "requirements", decision }),
                      }),
                    )
                  }
                />
              </div>
            ) : null}
          </section>
        ) : null}

        {can("generate_architecture") || snapshot.decisions.length > 0 ? (
          <section className="border border-line bg-white/70 p-5">
            <h2 className="font-serif text-2xl">Architecture</h2>
            <p className="mt-1 text-sm text-muted">
              Ownership says which directories an agent will be allowed to touch later. Two agents will not be
              scheduled on the same paths.
            </p>
            {can("generate_architecture") || can("rewrite_architecture") ? (
              <button
                type="button"
                disabled={busy}
                className="mt-4 bg-ink px-3 py-2 text-sm text-paper"
                onClick={() => run(() => api(`/api/projects/${project.id}/architecture`, { method: "POST" }))}
              >
                {snapshot.decisions.length ? "Rewrite architecture" : "Propose architecture"}
              </button>
            ) : null}
            {project.architecture_summary ? <p className="mt-4 leading-relaxed">{project.architecture_summary}</p> : null}
            {project.test_strategy ? (
              <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-3">
                {Object.entries(project.test_strategy).map(([tier, command]) => (
                  <div key={tier}>
                    <dt className="text-muted uppercase tracking-widest text-xs">{tier}</dt>
                    <dd className="font-mono text-sm">{command}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
            {snapshot.ownership.length > 0 ? (
              <ul className="mt-4 space-y-1 text-sm">
                {snapshot.ownership.map((rule) => (
                  <li key={rule.id}>
                    <span className="font-mono">{rule.glob}</span>
                    <span className="text-muted"> belongs to </span>
                    {rule.zone}
                  </li>
                ))}
              </ul>
            ) : null}
            <ul className="mt-4 space-y-4">
              {snapshot.decisions.map((decision) => (
                <li key={decision.id} className="border-t border-line pt-4">
                  <h3 className="font-serif text-xl">{decision.title}</h3>
                  <p className="mt-1 text-sm">{decision.context}</p>
                  <p className="mt-2 text-sm">
                    <span className="text-muted">Chose: </span>
                    {decision.decision}
                  </p>
                  <p className="mt-1 text-sm text-muted">{decision.consequences}</p>
                </li>
              ))}
            </ul>
            {can("approve_architecture") ? (
              <div className="mt-4">
                <GateButtons
                  busy={busy}
                  gate="architecture"
                  onDecide={(decision) =>
                    run(() =>
                      api(`/api/projects/${project.id}/gates`, {
                        method: "POST",
                        body: JSON.stringify({ gate: "architecture", decision }),
                      }),
                    )
                  }
                />
              </div>
            ) : null}
          </section>
        ) : null}

        {can("generate_tasks") || snapshot.tasks.length > 0 ? (
          <section className="border border-line bg-white/70 p-5">
            <h2 className="font-serif text-2xl">Tasks</h2>
            <p className="mt-1 text-sm text-muted">
              Ready means the orchestrator may claim it. The agent writes only inside its zone, on a branch,
              and the architecture&apos;s test commands must pass in a container before that branch is
              committed and a pull request is opened. Review runs those commands again, then checks the
              acceptance criteria. A failing command sends the task back. A criterion the review cannot
              execute waits for you to waive it or send the task back. Accepting a passed review rebases
              onto main, re-runs the checks, then merges and unblocks whatever was waiting. After too many
              failed attempts a task escalates and waits for you to resume it.
            </p>
            {status.needs_you.length > 0 ? (
              <p className="mt-4 border border-oxide bg-oxide-soft px-4 py-3 text-sm">
                Waiting on you: {status.needs_you.join(" · ")}. Answer + resume that task below, or
                keep running other ready work.
              </p>
            ) : null}
            {can("run_ready") ? (
              <button
                type="button"
                disabled={busy}
                className="mt-4 bg-ink px-3 py-2 text-sm text-paper"
                onClick={() => run(() => api(`/api/projects/${project.id}/tasks/run`, { method: "POST" }))}
              >
                Run the next ready task
              </button>
            ) : null}
            {can("generate_tasks") ? (
              <button
                type="button"
                disabled={busy}
                className="mt-4 bg-ink px-3 py-2 text-sm text-paper"
                onClick={() => run(() => api(`/api/projects/${project.id}/tasks`, { method: "POST" }))}
              >
                Break into tasks
              </button>
            ) : null}
            {project.uncovered_requirement_keys.length > 0 ? (
              <p className="mt-4 text-sm text-oxide">
                No task covers {project.uncovered_requirement_keys.join(", ")}.
              </p>
            ) : null}
            <ul className="mt-4 space-y-3">
              {[...snapshot.tasks]
                .sort((left, right) => taskPriority(left.state) - taskPriority(right.state))
                .map((task) => (
                <li key={task.id} className="flex gap-4 border-t border-line pt-3">
                  <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${dotClass(task.state)}`} />
                  <div>
                    <p className="text-xs tracking-widest text-muted uppercase">
                      {task.key} · {task.state.replaceAll("_", " ")} · {task.zone} · size {task.size}
                      {task.estimate_tokens
                        ? ` · ~${task.estimate_tokens.toLocaleString()} tokens`
                        : ""}
                    </p>
                    <h3 className="font-serif text-xl">{task.title}</h3>
                    <p className="text-sm">{task.description}</p>
                    <p className="mt-1 text-sm text-muted">
                      Covers {task.requirement_keys.join(", ")}
                      {task.depends_on.length ? ` · waits on ${task.depends_on.join(", ")}` : " · nothing blocks it"}
                      {task.branch_name ? ` · ${task.branch_name}` : ""}
                      {task.source_task_key ? ` · fixes ${task.source_task_key}` : ""}
                    </p>
                    <button
                      type="button"
                      disabled={detailBusy}
                      className="mt-2 border border-ink px-3 py-1 text-sm"
                      onClick={() => void inspectTask(task.id)}
                    >
                      {openTaskId === task.id ? "Hide detail" : "Inspect runs, diff, and checks"}
                    </button>
                    {openTaskId === task.id && taskDetail?.task.id === task.id ? (
                      <div className="mt-3 space-y-3 border border-line bg-paper px-3 py-3 text-sm">
                        <div>
                          <p className="text-xs tracking-widest text-muted uppercase">Runs</p>
                          {taskDetail.runs.length ? (
                            <ul className="mt-1 space-y-1">
                              {taskDetail.runs.map((item) => (
                                <li key={item.id}>
                                  {item.role} · {item.purpose} · {item.provider}/{item.model} ·{" "}
                                  {item.input_tokens + item.output_tokens} tokens
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="mt-1 text-muted">No agent runs yet.</p>
                          )}
                        </div>
                        <div>
                          <p className="text-xs tracking-widest text-muted uppercase">Checks</p>
                          {taskDetail.checks.length ? (
                            <ul className="mt-1 space-y-1">
                              {taskDetail.checks.map((check) => (
                                <li key={check.id} className={check.exit_code === 0 ? "text-muted" : "text-oxide"}>
                                  {check.tier} · exit {check.exit_code} · {check.command}
                                  {check.excerpt ? (
                                    <pre className="mt-1 overflow-x-auto whitespace-pre-wrap text-xs">{check.excerpt}</pre>
                                  ) : null}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="mt-1 text-muted">No check output yet.</p>
                          )}
                        </div>
                        <div>
                          <p className="text-xs tracking-widest text-muted uppercase">Pull requests</p>
                          {taskDetail.pull_requests.length ? (
                            <ul className="mt-1 space-y-2">
                              {taskDetail.pull_requests.map((pr) => (
                                <li key={pr.id}>
                                  <p>
                                    {pr.state}
                                    {pr.number != null ? ` #${pr.number}` : ""} · {pr.title}
                                  </p>
                                  <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-muted">
                                    {pr.body}
                                  </pre>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="mt-1 text-muted">No pull request yet.</p>
                          )}
                        </div>
                        <div>
                          <p className="text-xs tracking-widest text-muted uppercase">
                            Diff{taskDetail.diff_truncated ? " (truncated)" : ""}
                          </p>
                          {taskDetail.diff ? (
                            <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap text-xs">
                              {taskDetail.diff}
                            </pre>
                          ) : (
                            <p className="mt-1 text-muted">No branch diff yet.</p>
                          )}
                        </div>
                        {taskDetail.events.length ? (
                          <div>
                            <p className="text-xs tracking-widest text-muted uppercase">Task action log</p>
                            <ul className="mt-1 space-y-1 text-muted">
                              {taskDetail.events.slice(0, 12).map((event) => (
                                <li key={event.id}>
                                  <span className="uppercase tracking-widest text-xs">
                                    {event.kind ?? "outcome"}
                                  </span>
                                  {" · "}
                                  {event.type.replaceAll(".", " · ")}
                                  {typeof event.payload.summary === "string"
                                    ? event.actor_kind === "agent"
                                      ? ` — agent summary: ${event.payload.summary}`
                                      : ` — ${event.payload.summary}`
                                    : null}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {canAmend(task.state) && task.branch_name ? (
                          <form
                            className="space-y-2 border-t border-line pt-3"
                            onSubmit={(event) => {
                              event.preventDefault();
                              void amendBranch(task.id);
                            }}
                          >
                            <p className="text-xs tracking-widest text-muted uppercase">Amend the branch</p>
                            <p className="text-muted">
                              Write a file inside the {task.zone} zone. The next run sees your commit.
                            </p>
                            <input
                              required
                              disabled={busy || project.paused}
                              value={amendPath}
                              onChange={(event) => setAmendPath(event.target.value)}
                              placeholder="path/inside/zone.py"
                              className="w-full border border-line bg-paper px-2 py-1 font-mono text-xs"
                            />
                            <textarea
                              required
                              disabled={busy || project.paused}
                              value={amendContent}
                              onChange={(event) => setAmendContent(event.target.value)}
                              rows={6}
                              placeholder="File contents"
                              className="w-full border border-line bg-paper px-2 py-1 font-mono text-xs"
                            />
                            <input
                              disabled={busy || project.paused}
                              value={amendSummary}
                              onChange={(event) => setAmendSummary(event.target.value)}
                              placeholder="Short commit summary"
                              className="w-full border border-line bg-paper px-2 py-1 text-sm"
                            />
                            <button
                              type="submit"
                              disabled={busy || project.paused || !amendPath.trim()}
                              className="bg-ink px-3 py-2 text-sm text-paper"
                            >
                              Commit amendment
                            </button>
                          </form>
                        ) : null}
                      </div>
                    ) : null}
                    {canReassign(task.state) ? (
                      <label className="mt-2 flex items-center gap-2 text-sm">
                        Zone
                        <select
                          disabled={busy || project.paused}
                          value={task.zone}
                          className="border border-line bg-paper px-2 py-1"
                          onChange={(event) =>
                            void run(() =>
                              api(`/api/projects/${project.id}/tasks/${task.id}/reassign`, {
                                method: "POST",
                                body: JSON.stringify({ zone: event.target.value }),
                              }),
                            )
                          }
                        >
                          {[...new Set(snapshot.ownership.map((rule) => rule.zone))].map((zone) => (
                            <option key={zone} value={zone}>
                              {zone}
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : null}
                    {task.state === "escalated" ? (
                      <div className="mt-2 space-y-2 border border-oxide-soft bg-oxide-soft/40 p-3">
                        {(() => {
                          const question = [...snapshot.events]
                            .reverse()
                            .find(
                              (event) =>
                                event.type === "task.needs_clarification" &&
                                typeof event.payload?.key === "string" &&
                                event.payload.key === task.key,
                            );
                          const text =
                            typeof question?.payload?.clarification === "string"
                              ? question.payload.clarification
                              : typeof question?.payload?.summary === "string"
                                ? question.payload.summary
                                : "The agent needs a clarification before it can continue.";
                          return <p className="text-sm text-ink">Agent asked: {text}</p>;
                        })()}
                        <label className="block text-sm">
                          Your answer (optional — appended to the task)
                          <textarea
                            value={resumeAnswers[task.id] ?? ""}
                            onChange={(event) =>
                              setResumeAnswers((prev) => ({ ...prev, [task.id]: event.target.value }))
                            }
                            rows={2}
                            className="mt-1 w-full border border-line bg-paper px-3 py-2"
                            placeholder="e.g. Win = three in a row; response 'Congratulation {name} you won', status 200"
                          />
                        </label>
                        <button
                          type="button"
                          disabled={busy || project.paused}
                          className="bg-oxide px-3 py-2 text-sm text-white"
                          onClick={() =>
                            run(() =>
                              api(`/api/projects/${project.id}/tasks/${task.id}/resume`, {
                                method: "POST",
                                body: JSON.stringify({
                                  answer: (resumeAnswers[task.id] ?? "").trim() || null,
                                }),
                              }),
                            ).then(() =>
                              setResumeAnswers((prev) => {
                                const next = { ...prev };
                                delete next[task.id];
                                return next;
                              }),
                            )
                          }
                        >
                          Resume escalated task
                        </button>
                      </div>
                    ) : null}
                    {canCancel(task.state) ? (
                      <button
                        type="button"
                        disabled={busy || project.paused}
                        className="mt-2 border border-oxide px-3 py-2 text-sm text-oxide"
                        onClick={() =>
                          run(() => api(`/api/projects/${project.id}/tasks/${task.id}/cancel`, { method: "POST" }))
                        }
                      >
                        Cancel task
                      </button>
                    ) : null}
                    {task.state === "in_review" ? (
                      <div className="mt-2 flex flex-wrap gap-3">
                        <button
                          type="button"
                          disabled={busy || project.paused}
                          className="bg-ink px-3 py-2 text-sm text-paper"
                          onClick={() =>
                            run(() => api(`/api/projects/${project.id}/tasks/${task.id}/review`, { method: "POST" }))
                          }
                        >
                          Review against the criteria
                        </button>
                        {snapshot.findings.some(
                          (finding) => finding.task_id === task.id && finding.result === "untestable",
                        ) ? (
                          <>
                            <button
                              type="button"
                              disabled={busy || project.paused}
                              className="bg-moss px-3 py-2 text-sm text-white"
                              onClick={() =>
                                run(() =>
                                  api(`/api/projects/${project.id}/tasks/${task.id}/untestable`, {
                                    method: "POST",
                                    body: JSON.stringify({ decision: "waive" }),
                                  }),
                                )
                              }
                            >
                              Accept without those checks
                            </button>
                            <button
                              type="button"
                              disabled={busy || project.paused}
                              className="border border-ink px-3 py-2 text-sm"
                              onClick={() =>
                                run(() =>
                                  api(`/api/projects/${project.id}/tasks/${task.id}/untestable`, {
                                    method: "POST",
                                    body: JSON.stringify({ decision: "reject" }),
                                  }),
                                )
                              }
                            >
                              Send back
                            </button>
                          </>
                        ) : null}
                      </div>
                    ) : null}
                    {task.state === "gated" ? (
                      <button
                        type="button"
                        disabled={busy || project.paused}
                        className="mt-2 bg-moss px-3 py-2 text-sm text-white"
                        onClick={() =>
                          run(() => api(`/api/projects/${project.id}/tasks/${task.id}/accept`, { method: "POST" }))
                        }
                      >
                        Accept and merge
                      </button>
                    ) : null}
                    <ul className="mt-2 space-y-1 text-sm">
                      {snapshot.pull_requests
                        .filter((pr) => pr.task_id === task.id)
                        .map((pr) => (
                          <li key={pr.id}>
                            Pull request · {pr.state}
                            {pr.number != null ? ` #${pr.number}` : ""} · {pr.title}
                            {pr.url ? (
                              <>
                                {" "}
                                ·{" "}
                                <a href={pr.url} className="underline" target="_blank" rel="noreferrer">
                                  open on GitHub
                                </a>
                              </>
                            ) : null}
                          </li>
                        ))}
                      {snapshot.checks
                        .filter((check) => check.task_id === task.id)
                        .map((check) => (
                          <li key={check.id} className={check.exit_code === 0 ? "text-muted" : "text-oxide"}>
                            {check.tier} · exit {check.exit_code} · {check.command}
                            {check.excerpt ? ` — ${check.excerpt}` : ""}
                          </li>
                        ))}
                      {snapshot.findings
                        .filter((finding) => finding.task_id === task.id)
                        .map((finding) => (
                          <li key={finding.id}>
                            {finding.criterion_key} · {finding.result}
                            {finding.note ? ` — ${finding.note}` : ""}
                          </li>
                        ))}
                      {snapshot.defects
                        .filter((defect) => defect.task_id === task.id)
                        .map((defect) => (
                          <li key={defect.id} className="text-oxide">
                            {defect.criterion_key}: expected {defect.expected}, observed {defect.observed}. Reproduce:{" "}
                            {defect.reproduction}
                          </li>
                        ))}
                    </ul>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section>
          <h2 className="font-serif text-2xl">Action log</h2>
          <p className="mt-1 text-sm text-muted">
            Decisions, tools, artefacts, and outcomes. Agent-authored summaries are labelled as such — not as
            explanations of behaviour.
          </p>
          <ol className="mt-4 space-y-2 text-sm">
            {snapshot.events.map((event) => (
              <li
                key={event.id}
                className="grid grid-cols-[5.5rem_5.5rem_1fr] gap-3 border-t border-line py-2"
              >
                <time className="text-muted">{new Date(event.occurred_at).toLocaleTimeString()}</time>
                <span className="text-xs tracking-widest text-muted uppercase">
                  {event.kind ?? "outcome"}
                </span>
                <span>
                  {event.type.replaceAll(".", " · ")}
                  <span className="text-muted"> · {event.actor_role ?? event.actor_kind}</span>
                  {typeof event.payload.cause === "string" ? ` — ${event.payload.cause}` : null}
                  {typeof event.payload.summary === "string" ? (
                    <>
                      {" — "}
                      {event.actor_kind === "agent" ? (
                        <span className="text-muted">agent summary: {event.payload.summary}</span>
                      ) : (
                        event.payload.summary
                      )}
                    </>
                  ) : null}
                </span>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </main>
  );
}

function dotClass(state: string): string {
  if (state === "ready" || state === "done" || state === "gated") return "bg-moss";
  if (state === "blocked") return "bg-muted";
  return "bg-oxide";
}

function taskPriority(state: string): number {
  if (state === "escalated") return 0;
  if (state === "gated") return 1;
  if (state === "in_review") return 2;
  if (state === "ready") return 3;
  if (state === "in_progress") return 4;
  if (state === "blocked") return 5;
  return 6;
}

function canReassign(state: string): boolean {
  return (
    state === "ready" ||
    state === "blocked" ||
    state === "escalated" ||
    state === "failed" ||
    state === "changes_requested"
  );
}

function canAmend(state: string): boolean {
  return (
    state === "ready" ||
    state === "in_review" ||
    state === "gated" ||
    state === "changes_requested" ||
    state === "escalated"
  );
}

function canCancel(state: string): boolean {
  return (
    state === "draft" ||
    state === "blocked" ||
    state === "ready" ||
    state === "in_progress" ||
    state === "in_review" ||
    state === "gated" ||
    state === "changes_requested" ||
    state === "failed" ||
    state === "escalated"
  );
}

function GateButtons({
  busy,
  gate,
  onDecide,
}: {
  busy: boolean;
  gate: string;
  onDecide: (decision: "approved" | "rejected") => void;
}) {
  return (
    <div className="flex flex-wrap gap-3">
      <button type="button" disabled={busy} className="bg-moss px-3 py-2 text-sm text-white" onClick={() => onDecide("approved")}>
        Approve {gate}
      </button>
      <button type="button" disabled={busy} className="border border-ink px-3 py-2 text-sm" onClick={() => onDecide("rejected")}>
        Send back
      </button>
    </div>
  );
}

function RequirementForm({
  initial,
  busy,
  onSave,
  onCancel,
}: {
  initial: Requirement;
  busy: boolean;
  onSave: (body: { kind: Requirement["kind"]; title: string; statement: string; criteria: string[] }) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(initial.title);
  const [statement, setStatement] = useState(initial.statement);
  const [criteria, setCriteria] = useState(initial.criteria.map((item) => item.statement).join("\n"));
  return (
    <div className="space-y-2">
      <input value={title} onChange={(event) => setTitle(event.target.value)} className="w-full border border-line bg-paper px-3 py-2" />
      <textarea value={statement} onChange={(event) => setStatement(event.target.value)} rows={3} className="w-full border border-line bg-paper px-3 py-2" />
      <textarea
        value={criteria}
        onChange={(event) => setCriteria(event.target.value)}
        rows={4}
        className="w-full border border-line bg-paper px-3 py-2"
        placeholder="One acceptance criterion per line"
      />
      <div className="flex gap-3">
        <button
          type="button"
          disabled={busy}
          className="bg-ink px-3 py-2 text-sm text-paper"
          onClick={() =>
            onSave({
              kind: initial.kind,
              title,
              statement,
              criteria: criteria.split("\n").map((line) => line.trim()).filter(Boolean),
            })
          }
        >
          Save requirement
        </button>
        <button type="button" className="text-sm underline" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
