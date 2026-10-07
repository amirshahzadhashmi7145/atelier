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

const OfficeScene3D = dynamic(() => import("@/components/office/OfficeScene3D"), {
  ssr: false,
  loading: () => (
    <div className="office-stage mx-auto flex aspect-[16/10] w-full max-w-6xl items-center justify-center text-sm text-[#3f3124]/80">
      Warming the loft lights…
    </div>
  ),
});

function tone(state: string) {
  switch (state) {
    case "working":
      return { label: "Working", className: "text-moss" };
    case "waiting":
      return { label: "Waiting", className: "text-oxide" };
    case "blocked":
      return { label: "Blocked", className: "text-oxide" };
    case "done":
      return { label: "Done", className: "text-moss" };
    default:
      return { label: "Idle", className: "text-muted" };
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
          return;
        }
        const next = await Promise.all(list.map((project) => loadProject(project.id)));
        if (!alive) return;
        setSnapshots(next);
        setSyncedAt(Date.now());
        setError("");
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "The request failed.");
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
  const live = syncedAt != null && !error;
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

  return (
    <main className="office-page min-h-screen px-4 pb-16 pt-8 md:px-6 md:pt-10">
      <div className="mx-auto flex max-w-6xl flex-wrap items-end justify-between gap-6">
        <div>
          <Link href="/" className="text-xs uppercase tracking-[0.22em] text-oxide">
            Atelier
          </Link>
          <h1 className="font-serif mt-3 text-4xl leading-none tracking-tight text-[#1c1915] md:text-6xl">
            Coders Alley
          </h1>
          <p className="mt-3 max-w-xl text-[#3f3124]/85">
            Overall floor status across every project — desks light up from the hottest work in
            Atelier, not one board at a time.
          </p>
        </div>
        <div className="flex flex-col items-end gap-1 text-sm">
          <p className="text-xs uppercase tracking-[0.18em] text-[#3f3124]/70">Atelier overall</p>
          <p className="font-medium text-[#1c1915]">
            {projectCount === 0
              ? "No projects yet"
              : `${projectCount} project${projectCount === 1 ? "" : "s"} · ${activeProjects} active`}
          </p>
          <p className="text-xs text-[#3f3124]/70">
            Sync: <span className={live ? "text-moss" : ""}>{syncLabel}</span>
          </p>
          <Link href="/" className="text-oxide underline-offset-4 hover:underline">
            All projects
          </Link>
        </div>
      </div>

      {error ? <p className="mx-auto mt-6 max-w-6xl text-sm text-oxide">{error}</p> : null}

      <div className="mt-8 md:mt-10">
        <OfficeScene3D agents={agents} funTime={funTime} />
      </div>

      <section className="mx-auto mt-8 grid max-w-6xl gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="border border-[#2a2118]/20 bg-[#fffaf2]/88 shadow-sm backdrop-blur-sm">
          <div className="flex items-center justify-between border-b border-[#2a2118]/15 px-4 py-2 text-xs uppercase tracking-[0.16em] text-muted">
            <span>Desk status</span>
            <span>
              {projectCount === 0 ? "Waiting for a project" : `Merged from ${projectCount} project${projectCount === 1 ? "" : "s"} · ${syncLabel}`}
            </span>
          </div>
          <ul className="divide-y divide-line">
            {agents.map((agent) => {
              const t = tone(agent.state);
              return (
                <li
                  key={agent.id}
                  className="grid gap-1 px-4 py-3 md:grid-cols-[11rem_6rem_1fr_6rem] md:items-center"
                >
                  <div>
                    <p className="font-medium">{agent.label}</p>
                    <p className="text-xs text-muted">
                      {agent.roleTitle}
                      <span className="text-muted/80">
                        {" "}
                        · {agent.gender === "female" ? "Female" : "Male"}
                      </span>
                    </p>
                  </div>
                  <p className={`text-sm ${t.className}`}>{t.label}</p>
                  <p className="text-sm text-muted">
                    {agent.taskKey ? <span className="text-ink">{agent.taskKey} · </span> : null}
                    <span className="text-ink">{agent.activity}</span>
                    {agent.funLabel ? (
                      <span className="mt-0.5 block text-xs text-muted">Break: {agent.funLabel}</span>
                    ) : null}
                  </p>
                  <p className="text-xs text-muted md:text-right">{ago(agent.updatedAt)}</p>
                </li>
              );
            })}
          </ul>
          <div className="flex items-center justify-between border-y border-[#2a2118]/15 px-4 py-2 text-xs uppercase tracking-[0.16em] text-muted">
            <span>Floor staff</span>
            <span>Always on the floor</span>
          </div>
          <ul className="divide-y divide-line">
            {staff.map((person) => (
              <li
                key={person.id}
                className="grid gap-1 px-4 py-3 md:grid-cols-[11rem_6rem_1fr_6rem] md:items-center"
              >
                <div>
                  <p className="font-medium">{person.label}</p>
                  <p className="text-xs text-muted">
                    {person.roleTitle}
                    <span className="text-muted/80">
                      {" "}
                      · {person.gender === "female" ? "Female" : "Male"}
                    </span>
                  </p>
                </div>
                <p className="text-sm text-moss">On duty</p>
                <p className="text-sm text-ink">{person.dutyLabel}</p>
                <p className="text-xs text-muted md:text-right">floor</p>
              </li>
            ))}
          </ul>
        </div>

        <div className="border border-[#2a2118]/20 bg-[#fffaf2]/88 shadow-sm backdrop-blur-sm">
          <div className="border-b border-[#2a2118]/15 px-4 py-2 text-xs uppercase tracking-[0.16em] text-muted">
            Alley chatter
          </div>
          <ul className="max-h-[22rem] space-y-3 overflow-auto px-4 py-3">
            {chat.length === 0 ? (
              <li className="text-sm text-muted">Quiet floor… give it a few seconds.</li>
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
    <Suspense fallback={<main className="px-6 py-16 text-muted">Opening Coders Alley…</main>}>
      <OfficeInner />
    </Suspense>
  );
}
