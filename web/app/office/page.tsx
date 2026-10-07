"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { loadProject, loadProjects } from "@/lib/api";
import type { Snapshot } from "@/lib/types";
import {
  agentsFromSnapshots,
  chatFeed,
  demoAgents,
  floorStaff,
  withFunOverlay,
} from "@/components/office/agentLogic";
import { LiveDot, PageLoader, ProgressBar, Skeleton, Spinner } from "@/components/ui/feedback";

const OfficeScene3D = dynamic(() => import("@/components/office/OfficeScene3D"), {
  ssr: false,
  loading: () => (
    <div className="office-stage ui-panel mx-auto flex aspect-[16/10] w-full max-w-6xl flex-col items-center justify-center gap-3 text-sm text-[#3f3124]/80">
      <Spinner className="ui-spinner-lg" />
      <p>Warming the loft lights…</p>
      <div className="w-48">
        <ProgressBar indeterminate tone="amber" />
      </div>
    </div>
  ),
});

function tone(state: string) {
  switch (state) {
    case "working":
      return { label: "Working", className: "text-moss", bar: 78 as const };
    case "waiting":
      return { label: "Waiting", className: "text-oxide", bar: 42 as const };
    case "blocked":
      return { label: "Blocked", className: "text-oxide", bar: 18 as const };
    case "done":
      return { label: "Done", className: "text-moss", bar: 100 as const };
    default:
      return { label: "Idle", className: "text-muted", bar: 8 as const };
  }
}

function ago(iso?: string) {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms) || ms < 0) return "just now";
  if (ms < 2000) return "just now";
  if (ms < 60000) return `${Math.floor(ms / 1000)}s ago`;
  return `${Math.floor(ms / 60000)}m ago`;
}

function OfficeInner() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [error, setError] = useState("");
  const [syncedAt, setSyncedAt] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const [funTime, setFunTime] = useState(0);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const started = performance.now();
    const timer = window.setInterval(() => setFunTime((performance.now() - started) / 1000), 250);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const list = await loadProjects();
        if (!alive) return;
        if (!list.length) {
          setSnapshots([]);
          setSyncedAt(Date.now());
          setError("");
          setBooting(false);
          return;
        }
        const next = await Promise.all(list.map((project) => loadProject(project.id)));
        if (!alive) return;
        setSnapshots(next);
        setSyncedAt(Date.now());
        setError("");
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "The request failed.");
      } finally {
        if (alive) setBooting(false);
      }
    };
    poll();
    const timer = window.setInterval(poll, 2000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const baseAgents = snapshots.length ? agentsFromSnapshots(snapshots) : demoAgents();
  const agents = withFunOverlay(baseAgents, funTime);
  const staff = floorStaff(funTime);
  const chat = chatFeed(agents, funTime);
  const live = syncedAt != null && !error && now - syncedAt < 2500;
  const syncLabel =
    syncedAt == null ? "connecting…" : now - syncedAt < 2500 ? "live" : `${Math.floor((now - syncedAt) / 1000)}s ago`;
  const projectCount = snapshots.length;
  const activeProjects = snapshots.filter((snap) => {
    const stage = snap.project.stage;
    const busy = snap.tasks.some((task) =>
      ["in_progress", "in_review", "ready", "escalated", "blocked", "gated"].includes(task.state),
    );
    return busy || stage !== "tasks_ready";
  }).length;
  const workingAgents = agents.filter((a) => a.state === "working").length;
  const floorLoad = Math.round((workingAgents / Math.max(agents.length, 1)) * 100);

  return (
    <main className="office-page min-h-screen px-4 pb-16 pt-6 md:px-6 md:pt-8">
      <div className="mx-auto max-w-6xl">
        <nav className="atelier-nav border-b border-[#2a2118]/15">
          <Link href="/" className="atelier-brand text-[1.4rem] text-[#1c1915]">
            Atelier<span>.</span>
          </Link>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <LiveDot live={live} label={syncLabel} />
            <Link href="/" className="text-[#3f3124]/80 underline-offset-4 hover:underline">
              All projects
            </Link>
          </div>
        </nav>
      </div>

      <div className="mx-auto mt-8 flex max-w-6xl flex-wrap items-end justify-between gap-6">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-oxide">Floor view</p>
          <h1 className="font-serif mt-2 text-4xl leading-none tracking-tight text-[#1c1915] md:text-6xl">
            Coders Alley
          </h1>
          <p className="mt-3 max-w-xl text-[#3f3124]/85">
            Overall floor status across every project — desks light up from the hottest work in
            Atelier, not one board at a time.
          </p>
        </div>
        <div className="ui-panel min-w-[14rem] space-y-3 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-muted">Atelier overall</p>
          <p className="font-medium text-[#1c1915]">
            {projectCount === 0
              ? "No projects yet"
              : `${projectCount} project${projectCount === 1 ? "" : "s"} · ${activeProjects} active`}
          </p>
          <ProgressBar
            value={floorLoad}
            tone={floorLoad > 60 ? "moss" : floorLoad > 0 ? "amber" : "ink"}
            label="Desk load"
            detail={`${workingAgents}/${agents.length} working`}
          />
        </div>
      </div>

      {error ? <p className="mx-auto mt-6 max-w-6xl text-sm text-oxide">{error}</p> : null}

      <div className="mt-8 md:mt-10">
        {booting ? (
          <div className="office-stage ui-panel mx-auto flex aspect-[16/10] w-full max-w-6xl flex-col items-center justify-center gap-3">
            <Spinner className="ui-spinner-lg" />
            <p className="text-sm text-muted">Syncing the floor…</p>
            <div className="w-52">
              <ProgressBar indeterminate tone="moss" />
            </div>
          </div>
        ) : (
          <OfficeScene3D agents={agents} funTime={funTime} />
        )}
      </div>

      <section className="mx-auto mt-8 grid max-w-6xl gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="ui-panel overflow-hidden">
          <div className="flex items-center justify-between border-b border-[#2a2118]/12 px-4 py-2.5 text-xs uppercase tracking-[0.16em] text-muted">
            <span>Desk status</span>
            <span>
              {projectCount === 0
                ? "Waiting for a project"
                : `Merged from ${projectCount} project${projectCount === 1 ? "" : "s"}`}
            </span>
          </div>
          {booting ? (
            <div className="space-y-3 p-4">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {agents.map((agent) => {
                const t = tone(agent.state);
                return (
                  <li key={agent.id} className="grid gap-2 px-4 py-3 md:grid-cols-[11rem_1fr_6rem] md:items-center">
                    <div>
                      <p className="font-medium">{agent.label}</p>
                      <p className="text-xs text-muted">{agent.roleTitle}</p>
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        {agent.state === "working" ? <Spinner /> : null}
                        <p className={`text-sm ${t.className}`}>{t.label}</p>
                      </div>
                      <p className="mt-0.5 truncate text-sm text-muted">
                        {agent.taskKey ? <span className="text-ink">{agent.taskKey} · </span> : null}
                        <span className="text-ink">{agent.activity}</span>
                        {agent.funLabel ? (
                          <span className="text-muted"> · {agent.funLabel}</span>
                        ) : null}
                      </p>
                      <div className="mt-2 max-w-xs">
                        <ProgressBar
                          value={t.bar}
                          tone={agent.state === "blocked" ? "oxide" : agent.state === "working" ? "moss" : "ink"}
                        />
                      </div>
                    </div>
                    <p className="text-xs text-muted md:text-right">{ago(agent.updatedAt)}</p>
                  </li>
                );
              })}
            </ul>
          )}
          <div className="flex items-center justify-between border-y border-[#2a2118]/12 px-4 py-2.5 text-xs uppercase tracking-[0.16em] text-muted">
            <span>Floor staff</span>
            <span>Always on duty</span>
          </div>
          <ul className="divide-y divide-line">
            {staff.map((person) => (
              <li
                key={person.id}
                className="grid gap-1 px-4 py-3 md:grid-cols-[11rem_6rem_1fr_6rem] md:items-center"
              >
                <div>
                  <p className="font-medium">{person.label}</p>
                  <p className="text-xs text-muted">{person.roleTitle}</p>
                </div>
                <p className="inline-flex items-center gap-1.5 text-sm text-moss">
                  <span className="ui-live-dot" style={{ background: "var(--color-moss)" }} />
                  On duty
                </p>
                <p className="text-sm text-ink">{person.dutyLabel}</p>
                <p className="text-xs text-muted md:text-right">floor</p>
              </li>
            ))}
          </ul>
        </div>

        <div className="ui-panel overflow-hidden">
          <div className="border-b border-[#2a2118]/12 px-4 py-2.5 text-xs uppercase tracking-[0.16em] text-muted">
            Alley chatter
          </div>
          <ul className="max-h-[22rem] space-y-3 overflow-auto px-4 py-3">
            {chat.length === 0 ? (
              <li className="flex items-center gap-2 text-sm text-muted">
                <Spinner /> Quiet floor… give it a few seconds.
              </li>
            ) : (
              chat.map((line) => (
                <li key={line.id} className="text-sm leading-snug">
                  <span className="font-medium text-ink">{line.from}</span>
                  <span className="text-muted"> · </span>
                  <span className="text-muted">“{line.text}”</span>
                </li>
              ))
            )}
          </ul>
        </div>
      </section>
    </main>
  );
}

export default function OfficePage() {
  return (
    <Suspense fallback={<PageLoader label="Opening Coders Alley…" />}>
      <OfficeInner />
    </Suspense>
  );
}
