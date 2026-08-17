export type StatusOption = { value: string; label: string };

export type ProjectTask = {
  id: string;
  name: string;
  description: string;
  renderer_key: string;
  capabilities: string[];
  statuses: StatusOption[];
};

export type Project = {
  id: string;
  name: string;
  description: string;
  tasks: ProjectTask[];
};

export type ReviewItemSummary = {
  id: string;
  title: string;
  subtitle?: string;
  status: string;
  badges: string[];
};

export type ReviewListResponse = {
  project_id: string;
  task_id: string;
  dataset_version: string;
  total: number;
  counts: Record<string, number>;
  items: ReviewItemSummary[];
};

export type ReviewRecord = {
  project_id: string;
  task_id: string;
  item_id: string;
  dataset_version: string;
  revision: number;
  status: string;
  values: Record<string, unknown>;
  note: string;
  created_at: string;
  updated_at: string;
};

export type ReviewItem = {
  id: string;
  title: string;
  status: string;
  source: Record<string, unknown>;
  prediction: Record<string, unknown>;
  review: Partial<ReviewRecord>;
  metadata: Record<string, unknown>;
};

export type ReviewPatch = {
  status: string;
  values: Record<string, unknown>;
  note: string;
};

export type SaveState = "idle" | "saving" | "saved" | "error";
