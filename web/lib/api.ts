import type { ProjectListItem, Snapshot, TaskDetail } from "./types";

function baseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : "The request failed.");
  }
  return data as T;
}

export const loadProjects = () => api<ProjectListItem[]>("/api/projects");
export const loadProject = (id: string) => api<Snapshot>(`/api/projects/${id}`);
export const loadTaskDetail = (projectId: string, taskId: string) =>
  api<TaskDetail>(`/api/projects/${projectId}/tasks/${taskId}`);

export function postProject(body: {
  name: string;
  description: string;
  tech_preferences?: string;
  github_repo?: string;
}) {
  return api<Snapshot>("/api/projects", { method: "POST", body: JSON.stringify(body) });
}
