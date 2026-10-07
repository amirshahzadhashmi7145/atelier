"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { loadProjects, postProject } from "@/lib/api";
import type { ProjectListItem } from "@/lib/types";

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
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[70vh] bg-[radial-gradient(ellipse_at_20%_0%,#efe2d0_0%,transparent_55%),radial-gradient(ellipse_at_90%_10%,#dfe8d4_0%,transparent_40%)]" />

      <section className="relative mx-auto grid max-w-6xl gap-12 px-6 pb-8 pt-14 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
        <div>
          <p className="text-xs tracking-[0.28em] text-oxide uppercase">Atelier</p>
          <h1 className="font-serif mt-4 max-w-xl text-5xl leading-[0.95] md:text-6xl">
            Describe it.
            <span className="block text-muted">Watch the team build.</span>
          </h1>
          <p className="mt-5 max-w-lg text-lg leading-relaxed text-muted">
            PM plans. Engineers take desks by zone. QA reviews. You approve the gates that matter.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <a
              href="#start"
              className="bg-ink px-5 py-2.5 text-sm text-paper transition hover:bg-[#2c261f]"
            >
              Start a project
            </a>
            <Link
              href="/office"
              className="border border-ink/20 bg-white/50 px-5 py-2.5 text-sm transition hover:border-ink/40"
            >
              Coders Alley
            </Link>
          </div>
        </div>

        <Link
          href="/office"
          className="group relative block aspect-[5/4] overflow-hidden border border-line bg-[#cbb89a] transition"
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
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#1c1915]/70 to-transparent px-4 py-4">
            <p className="text-xs uppercase tracking-[0.22em] text-[#f3efe6]/80">Live mezzanine</p>
            <p className="font-serif text-2xl text-paper">Coders Alley</p>
          </div>
        </Link>
      </section>

      <section id="start" className="relative mx-auto max-w-6xl px-6 pb-20 pt-6">
        <div className="grid gap-10 lg:grid-cols-[1fr_0.9fr]">
          <form onSubmit={onSubmit} className="space-y-4 border border-line bg-white/55 p-6 backdrop-blur-sm">
            <h2 className="font-serif text-3xl">Start a project</h2>
            <label className="block text-sm">
              Name
              <input
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="mt-1 w-full border border-line bg-paper px-3 py-2"
                placeholder="Task manager"
              />
            </label>
            <label className="block text-sm">
              What should it do?
              <textarea
                required
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={5}
                className="mt-1 w-full border border-line bg-paper px-3 py-2"
                placeholder="A task manager with email login, projects, assignment, and due dates."
              />
            </label>
            <label className="block text-sm">
              GitHub repository <span className="text-muted">(optional, owner/name)</span>
              <input
                value={githubRepo}
                onChange={(event) => setGithubRepo(event.target.value)}
                className="mt-1 w-full border border-line bg-paper px-3 py-2"
                placeholder="acme/notes"
              />
            </label>
            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                checked={createGithubRepo}
                onChange={(event) => setCreateGithubRepo(event.target.checked)}
                className="mt-1"
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
                className="mt-1 w-full border border-line bg-paper px-3 py-2"
                placeholder="TypeScript, Python"
              />
            </label>
            {error ? <p className="text-sm text-oxide">{error}</p> : null}
            <button type="submit" disabled={busy} className="bg-ink px-4 py-2 text-sm text-paper">
              {busy ? "Creating…" : "Start a project"}
            </button>
          </form>

          <section>
            <div className="flex items-baseline justify-between gap-4">
              <h2 className="font-serif text-3xl">Projects</h2>
              <Link href="/office" className="text-sm text-oxide underline-offset-4 hover:underline">
                Coders Alley
              </Link>
            </div>
            {!loaded ? (
              <p className="mt-3 text-sm text-muted">Loading projects…</p>
            ) : projects.length === 0 ? (
              <p className="mt-3 text-sm text-muted">None yet — start one and watch the desks wake up.</p>
            ) : (
              <ul className="mt-4 divide-y divide-line border-y border-line">
                {projects.map((project) => (
                  <li key={project.id} className="flex items-center justify-between gap-3 py-3">
                    <Link href={`/projects/${project.id}`} className="min-w-0 flex-1">
                      <span className="block truncate">{project.name}</span>
                      <span className="text-sm text-muted">{project.stage.replaceAll("_", " ")}</span>
                    </Link>
                    <Link
                      href={`/office?project=${project.id}`}
                      className="shrink-0 text-sm text-oxide underline-offset-4 hover:underline"
                    >
                      Watch
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}
