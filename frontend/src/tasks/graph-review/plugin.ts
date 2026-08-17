import type { ReviewItem, ReviewPatch } from "../../types";
import type { TaskPlugin } from "../types";
import { GraphReviewView } from "./GraphReviewView";
import {
  isGraphEdge,
  isGraphNode,
  requireGraphReviewDraft,
  requireGraphReviewItem,
  type GraphEdge,
  type GraphNode,
  type GraphReviewDraft,
} from "./types";

function cloneNodes(nodes: GraphNode[]): GraphNode[] {
  return nodes.map((node) => ({ ...node }));
}

function cloneEdges(edges: GraphEdge[]): GraphEdge[] {
  return edges.map((edge) => ({ ...edge }));
}

function createDraft(item: ReviewItem): GraphReviewDraft {
  const value = requireGraphReviewItem(item);
  const candidate = value.prediction.graph_candidate;
  const stored = value.review.values as Record<string, unknown> | undefined;
  const storedNodes = stored?.final_nodes;
  const storedEdges = stored?.final_edges;
  const nodes =
    Array.isArray(storedNodes) && storedNodes.every(isGraphNode)
      ? storedNodes
      : candidate.nodes;
  const edges =
    Array.isArray(storedEdges) && storedEdges.every(isGraphEdge)
      ? storedEdges
      : candidate.edges;
  return {
    status: value.status || "pending",
    nodes: cloneNodes(nodes),
    edges: cloneEdges(edges),
    reviewer:
      (stored?.reviewer as string | undefined) ??
      window.localStorage.getItem("review-workspace.reviewer") ??
      "",
    note: value.review.note ?? "",
  };
}

function toReviewPatch(value: unknown): ReviewPatch {
  const draft = requireGraphReviewDraft(value);
  return {
    status: draft.status,
    values: {
      graph_schema_version: "demo-graph-review-v1",
      final_nodes: cloneNodes(draft.nodes),
      final_edges: cloneEdges(draft.edges),
      reviewer: draft.reviewer,
    },
    note: draft.note,
  };
}

export const graphReviewTaskPlugin: TaskPlugin = {
  key: "graph_review",
  createDraft,
  toReviewPatch,
  onSaved(value) {
    const draft = requireGraphReviewDraft(value);
    window.localStorage.setItem("review-workspace.reviewer", draft.reviewer);
  },
  View: GraphReviewView,
};
