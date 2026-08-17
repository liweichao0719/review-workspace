import type { ReviewItem, ReviewRecord } from "../../types";

export type GraphNode = {
  id: string;
  type: string;
  label: string;
  evidence: string;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  evidence: string;
};

export type GraphCandidate = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type GraphReviewItem = ReviewItem & {
  source: {
    title: string;
    text: string;
    source_name: string;
    published_at: string;
    language: string;
  };
  prediction: {
    graph_candidate: GraphCandidate;
  };
  review: Partial<ReviewRecord>;
  metadata: {
    position: number;
    synthetic: boolean;
  };
};

export type GraphReviewDraft = {
  status: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  reviewer: string;
  note: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isGraphNode(value: unknown): value is GraphNode {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.type === "string" &&
    typeof value.label === "string" &&
    typeof value.evidence === "string"
  );
}

export function isGraphEdge(value: unknown): value is GraphEdge {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.source === "string" &&
    typeof value.target === "string" &&
    typeof value.type === "string" &&
    typeof value.evidence === "string"
  );
}

function isGraphCandidate(value: unknown): value is GraphCandidate {
  return (
    isRecord(value) &&
    Array.isArray(value.nodes) &&
    value.nodes.every(isGraphNode) &&
    Array.isArray(value.edges) &&
    value.edges.every(isGraphEdge)
  );
}

export function requireGraphReviewItem(item: ReviewItem): GraphReviewItem {
  const source = item.source;
  const candidate = item.prediction.graph_candidate;
  if (
    typeof source.title !== "string" ||
    typeof source.text !== "string" ||
    typeof source.source_name !== "string" ||
    typeof source.published_at !== "string" ||
    typeof source.language !== "string" ||
    !isGraphCandidate(candidate) ||
    typeof item.metadata.position !== "number"
  ) {
    throw new Error(`Invalid graph review item: ${item.id}`);
  }
  return item as GraphReviewItem;
}

export function requireGraphReviewDraft(draft: unknown): GraphReviewDraft {
  if (
    !isRecord(draft) ||
    typeof draft.status !== "string" ||
    !Array.isArray(draft.nodes) ||
    !draft.nodes.every(isGraphNode) ||
    !Array.isArray(draft.edges) ||
    !draft.edges.every(isGraphEdge) ||
    typeof draft.reviewer !== "string" ||
    typeof draft.note !== "string"
  ) {
    throw new Error("Invalid graph review draft");
  }
  return draft as GraphReviewDraft;
}
