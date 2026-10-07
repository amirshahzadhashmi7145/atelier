"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { loadProject, loadProjects } from "@/lib/api";
import type { ProjectListItem, Snapshot } from "@/lib/types";
import {
  agentsFromSnapshot,
  chatFeed,
  demoAgents,
  withFunOverlay,
} from "@/components/office/agentLogic";

const OfficeScene3D = dynamic(() => import("@/components/office/OfficeScene3D"), {
  ssr: false,
  loading: () => (
    <div className="mx-auto flex aspect-[16/11] w-full max-w-5xl items-center justify-center border border-line bg-[#cfc3ae] text-sm text-muted">
      Opening Coders Alley…
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
  const params = useSearchParams();
  const projectId = params.get("project");
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(projectId ?? "");
  const [syncedAt, setSyncedAt] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const [funTime, setFunTime] = useState(0);

  useEffect(() => {
    loadProjects()
      .then(setProjects)
      .catch((err: Error) => setError(err.message));
  }, []);

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
    if (!selected) {
      setSnapshot(null);
      setSyncedAt(null);
      return;
    }
    let alive = true;
    const poll = () => {
      loadProject(selected)
        .then((next) => {
          if (!alive) return;
          setSnapshot(next);
          setSyncedAt(Date.now());
          setError("");
        })
        .catch((err: Error) => {
          if (alive) setError(err.message);
        });
    };
    poll();
    const timer = window.setInterval(poll, 1500);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [selected]);

  const agents = withFunOverlay(snapshot ? agentsFromSnapshot(snapshot) : demoAgents(), funTime);
  const chat = chatFeed(agents, funTime);
  const live = Boolean(snapshot);
  const syncLabel =
    syncedAt == null ? "not synced" : now - syncedAt < 2000 ? "live" : `${Math.floor((now - syncedAt) / 1000)}s ago`;

  return (
    <main className="office-page min-h-screen px-6 pb-16 pt-10">
      <div className="mx-auto flex max-w-5xl flex-wrap items-end justify-between gap-6">
        <div>
          <Link href="/" className="text-xs uppercase tracking-[0.22em] text-oxide">
            Atelier
          </Link>
          <h1 className="font-serif mt-3 text-4xl leading-none md:text-5xl">Coders Alley</h1>
          <p className="mt-3 max-w-xl text-muted">
            Live work status from the API. Off-duty: coffee, foosball, patio smokes when idle or
            stressed, office dog, paper planes, microwave raids, naps, and victory dances.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2 text-sm">
          <label className="text-xs uppercase tracking-[0.18em] text-muted">Live project</label>
          <select
            value={selected}
            onChange={(event) => setSelected(event.target.value)}
            className="min-w-[14rem] border border-line bg-[#fffaf2] px-3 py-2"
          >
            <option value="">Idle preview (pick a project)</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted">
            Sync: <span className={live ? "text-moss" : ""}>{live ? syncLabel : "demo idle"}</span>
          </p>
          {selected ? (
            <Link href={`/projects/${selected}`} className="text-oxide underline-offset-4 hover:underline">
              Open project board
            </Link>
          ) : null}
        </div>
      </div>

      {error ? <p className="mx-auto mt-6 max-w-5xl text-sm text-oxide">{error}</p> : null}

      <div className="mt-10">
        <OfficeScene3D agents={agents} funTime={funTime} />
      </div>

      <section className="mx-auto mt-8 grid max-w-5xl gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="border border-line bg-[#fffaf2]/80">
          <div className="flex items-center justify-between border-b border-line px-4 py-2 text-xs uppercase tracking-[0.16em] text-muted">
            <span>Desk status</span>
            <span>{live ? `API ${syncLabel}` : "Select a project for live status"}</span>
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
                    {agent.dialogue ? (
                      <span className="text-ink">“{agent.dialogue}”</span>
                    ) : agent.funLabel ? (
                      <span className="text-ink">{agent.funLabel}</span>
                    ) : (
                      <>
                        {agent.taskKey ? <span className="text-ink">{agent.taskKey} · </span> : null}
                        {agent.activity}
                      </>
                    )}
                  </p>
                  <p className="text-xs text-muted md:text-right">{ago(agent.updatedAt)}</p>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="border border-line bg-[#fffaf2]/80">
          <div className="border-b border-line px-4 py-2 text-xs uppercase tracking-[0.16em] text-muted">
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
