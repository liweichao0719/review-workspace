import type {
  Project,
  ReviewItem,
  ReviewListResponse,
  ReviewPatch,
  ReviewRecord,
} from "./types";

const API = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Keep the HTTP status when the server did not return JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function getProjects(): Promise<Project[]> {
  return request<Project[]>("/projects");
}

export function getItems(
  projectId: string,
  taskId: string,
  query: string,
  status: string,
): Promise<ReviewListResponse> {
  const params = new URLSearchParams();
  if (query) params.set("query", query);
  if (status !== "all") params.set("status", status);
  return request<ReviewListResponse>(
    `/projects/${projectId}/tasks/${taskId}/items?${params.toString()}`,
  );
}

export function getItem(
  projectId: string,
  taskId: string,
  itemId: string,
): Promise<ReviewItem> {
  return request<ReviewItem>(
    `/projects/${projectId}/tasks/${taskId}/items/${itemId}`,
  );
}

export function saveReview(
  projectId: string,
  taskId: string,
  itemId: string,
  patch: ReviewPatch,
): Promise<ReviewRecord> {
  return request<ReviewRecord>(
    `/projects/${projectId}/tasks/${taskId}/items/${itemId}/review`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    },
  );
}

export function exportUrl(projectId: string, taskId: string): string {
  return `${API}/projects/${projectId}/tasks/${taskId}/export`;
}
