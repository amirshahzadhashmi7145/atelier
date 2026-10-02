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
      });
      router.push(`/projects/${snapshot.project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the project.");
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <p className="text-xs tracking-[0.22em] text-oxide uppercase">Atelier</p>
      <h1 className="font-serif mt-3 text-5xl leading-tight">Describe it. Approve the plan.</h1>
      <p className="mt-4 max-w-xl text-lg leading-relaxed text-muted">
        This phase stops at a task graph. A project manager agent turns your description into
        questions, requirements a test can fail, an architecture, and tasks. Nothing is merged,
        and no code is written, until you pass the gates.
      </p>

      <form onSubmit={onSubmit} className="mt-10 space-y-4 border border-line bg-white/60 p-6">
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

      <section className="mt-12">
        <h2 className="font-serif text-2xl">Projects</h2>
        {!loaded ? (
          <p className="mt-3 text-sm text-muted">Loading projects…</p>
        ) : projects.length === 0 ? (
          <p className="mt-3 text-sm text-muted">None yet.</p>
        ) : (
          <ul className="mt-4 divide-y divide-line border-y border-line">
            {projects.map((project) => (
              <li key={project.id}>
                <Link href={`/projects/${project.id}`} className="flex items-baseline justify-between py-3">
                  <span>{project.name}</span>
                  <span className="text-sm text-muted">{project.stage.replaceAll("_", " ")}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
