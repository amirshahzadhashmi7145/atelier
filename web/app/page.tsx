"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { loadProjects, postProject } from "@/lib/api";
import type { ProjectListItem } from "@/lib/types";
import { planProgressPct, planStepIndex, PLAN_STEPS } from "@/lib/progress";
import {
  BusyButton,
  EmptyHint,
  LiveDot,
  ProgressBar,
  Skeleton,
  Spinner,
} from "@/components/ui/feedback";

export default function HomePage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tech, setTech] = useState("");
  const [githubRepo, setGithubRepo] = useState("");
  const [createGithubRepo, setCreateGithubRepo] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    loadProjects()
      .then(setProjects)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoaded(true));
  }, []);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const snapshot = await postProject({
        name,
        description,
        tech_preferences: tech || undefined,
        github_repo: githubRepo || undefined,
        create_github_repo: createGithubRepo,
      });
      router.push(`/projects/${snapshot.project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the project.");
      setBusy(false);
    }
  }

  return (
    <main className="atelier-shell relative overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[72vh] bg-[radial-gradient(ellipse_at_18%_0%,#efe2d0_0%,transparent_55%),radial-gradient(ellipse_at_92%_8%,#dfe8d4_0%,transparent_42%),linear-gradient(180deg,rgba(255,248,239,0.65),transparent_50%)]" />
      <div className="pointer-events-none absolute -right-24 top-40 h-72 w-72 rounded-full bg-[radial-gradient(circle,rgba(154,52,18,0.08),transparent_70%)]" />

      <div className="relative mx-auto max-w-6xl px-6 pt-6">
        <nav className="atelier-nav">
          <Link href="/" className="atelier-brand">
            Atelier<span>.</span>
          </Link>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <LiveDot live={loaded} label={loaded ? "Ready" : "Loading"} />
            <Link href="/office" className="text-muted transition hover:text-ink">
              Coders Alley
            </Link>
            <a href="#start" className="ui-btn bg-ink px-4 py-2 text-sm text-paper">
              Start a project
            </a>
          </div>
        </nav>
      </div>

      <section className="relative mx-auto grid max-w-6xl gap-12 px-6 pb-10 pt-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-end">
        <div>
          <h1 className="font-serif text-6xl leading-[0.92] tracking-tight md:text-7xl">
            Atelier
          </h1>
          <p className="font-serif mt-4 max-w-xl text-2xl leading-snug text-muted md:text-3xl">
            Describe it. Watch the team build.
          </p>
          <p className="mt-5 max-w-lg text-base leading-relaxed text-muted md:text-lg">
            PM plans. Engineers take desks by zone. QA reviews. You approve the gates that matter —
            with live status the whole way.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <a href="#start" className="ui-btn bg-ink px-5 py-2.5 text-sm text-paper hover:bg-[#2c261f]">
              Start a project
            </a>
            <Link
              href="/office"
              className="ui-btn border border-ink/20 bg-white/55 px-5 py-2.5 text-sm backdrop-blur-sm hover:border-ink/40"
            >
              Open Coders Alley
            </Link>
          </div>
        </div>

        <Link
          href="/office"
          className="group relative block aspect-[5/4] overflow-hidden border border-line bg-[#cbb89a] shadow-[0_28px_50px_-32px_rgba(28,25,21,0.65)] transition duration-300 hover:-translate-y-1"
          aria-label="Open Coders Alley"
        >
          <div className="absolute inset-0 opacity-90 office-mini">
            <div className="absolute left-[18%] top-[28%] h-14 w-20 rotate-[-6deg] bg-[#6b4f35]" />
            <div className="absolute right-[16%] top-[34%] h-14 w-20 rotate-[8deg] bg-[#6b4f35]" />
            <div className="absolute left-[38%] top-[12%] h-10 w-24 bg-[#f7f4ee]" />
            <div className="absolute bottom-[22%] left-[30%] h-16 w-28 rounded-[40%] bg-[#d8cfc0]/80" />
            <span className="absolute left-[22%] top-[22%] h-3 w-3 rounded-full bg-moss" />
            <span className="absolute right-[24%] top-[30%] h-3 w-3 rounded-full bg-oxide" />
            <span className="absolute bottom-[30%] left-[48%] h-3 w-3 rounded-full bg-muted" />
          </div>
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#1c1915]/75 to-transparent px-4 py-4">
            <p className="text-xs uppercase tracking-[0.22em] text-[#f3efe6]/80">Live mezzanine</p>
            <p className="font-serif text-2xl text-paper">Coders Alley</p>
          </div>
        </Link>
      </section>

      <section id="start" className="relative mx-auto max-w-6xl px-6 pb-20 pt-4">
        <div className="grid gap-10 lg:grid-cols-[1.05fr_0.95fr]">
          <form onSubmit={onSubmit} className="ui-panel space-y-4 p-6 md:p-7">
            <div className="ui-panel-header">
              <h2 className="font-serif text-3xl">Start a project</h2>
              {busy ? <LiveDot live label="Creating" /> : null}
            </div>
            {busy ? <ProgressBar indeterminate tone="oxide" label="Preparing the workshop" detail="Hang tight" /> : null}
            <label className="block text-sm">
              Name
              <input
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="mt-1 w-full border border-line bg-paper/80 px-3 py-2.5 outline-none transition focus:border-ink/35"
                placeholder="Task manager"
                disabled={busy}
              />
            </label>
            <label className="block text-sm">
              What should it do?
              <textarea
                required
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={5}
                className="mt-1 w-full border border-line bg-paper/80 px-3 py-2.5 outline-none transition focus:border-ink/35"
                placeholder="A task manager with email login, projects, assignment, and due dates."
                disabled={busy}
              />
            </label>
            <label className="block text-sm">
              GitHub repository <span className="text-muted">(optional, owner/name)</span>
              <input
                value={githubRepo}
                onChange={(event) => setGithubRepo(event.target.value)}
                className="mt-1 w-full border border-line bg-paper/80 px-3 py-2.5 outline-none transition focus:border-ink/35"
                placeholder="acme/notes"
                disabled={busy}
              />
            </label>
            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                checked={createGithubRepo}
                onChange={(event) => setCreateGithubRepo(event.target.checked)}
                className="mt-1"
                disabled={busy}
              />
              <span>
                Create GitHub repository if missing
                <span className="mt-1 block text-muted">
                  Uses GITHUB_TOKEN. Empty name → auto slug from the project title under your account.
                </span>
              </span>
            </label>
            <label className="block text-sm">
              Technology preferences <span className="text-muted">(optional)</span>
              <input
                value={tech}
                onChange={(event) => setTech(event.target.value)}
                className="mt-1 w-full border border-line bg-paper/80 px-3 py-2.5 outline-none transition focus:border-ink/35"
                placeholder="TypeScript, Python"
                disabled={busy}
              />
            </label>
            {error ? <p className="text-sm text-oxide">{error}</p> : null}
            <BusyButton
              type="submit"
              busy={busy}
              busyLabel="Creating project…"
              className="bg-ink px-4 py-2.5 text-sm text-paper hover:bg-[#2c261f]"
            >
              Start a project
            </BusyButton>
          </form>

          <section>
            <div className="flex items-baseline justify-between gap-4">
              <h2 className="font-serif text-3xl">Projects</h2>
              <Link href="/office" className="text-sm text-oxide underline-offset-4 hover:underline">
                Watch the floor
              </Link>
            </div>

            {!loaded ? (
              <div className="mt-5 space-y-3" aria-busy>
                <div className="flex items-center gap-2 text-sm text-muted">
                  <Spinner /> Loading projects…
                </div>
                {[0, 1, 2].map((i) => (
                  <div key={i} className="ui-panel space-y-3 p-4">
                    <Skeleton className="h-4 w-2/5" />
                    <Skeleton className="h-3 w-1/3" />
                    <Skeleton className="h-2 w-full" />
                  </div>
                ))}
              </div>
            ) : projects.length === 0 ? (
              <EmptyHint>None yet — start one and watch the desks wake up.</EmptyHint>
            ) : (
              <ul className="mt-5 space-y-3">
                {projects.map((project) => {
                  const pct = planProgressPct(project.stage);
                  const step = PLAN_STEPS[planStepIndex(project.stage)]?.label ?? project.stage;
                  return (
                    <li key={project.id}>
                      <Link href={`/projects/${project.id}`} className="ui-project-card">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="truncate font-medium">{project.name}</p>
                            <p className="mt-0.5 text-sm text-muted">
                              {step}
                              <span className="text-muted/70"> · {project.stage.replaceAll("_", " ")}</span>
                            </p>
                          </div>
                          <span className="shrink-0 text-xs uppercase tracking-[0.14em] text-oxide">
                            Open
                          </span>
                        </div>
                        <div className="mt-3">
                          <ProgressBar
                            value={pct}
                            tone={pct >= 100 ? "moss" : "ink"}
                            detail={`${pct}%`}
                          />
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}
