import type { ReviewItem, ReviewPatch } from "../../types";
import type { TaskPlugin } from "../types";
import { FidicRagView } from "./FidicRagView";
import {
  requireFidicRagDraft,
  requireFidicRagItem,
  type FidicRagDraft,
} from "./types";

function createDraft(item: ReviewItem): FidicRagDraft {
  const value = requireFidicRagItem(item);
  const candidate = value.prediction.context_audit;
  const stored = value.review.values as Record<string, unknown> | undefined;
  const reviewer =
    (stored?.reviewer as string | undefined) ??
    window.localStorage.getItem("review-workspace.reviewer") ??
    "";
  return {
    status: value.status || "pending",
    taskType:
      (stored?.final_task_type as string | undefined) ?? candidate.suggested_task_type,
    questionQuality:
      (stored?.final_question_quality as string | undefined) ?? candidate.question_quality,
    revisedQuestion:
      (stored?.revised_question as string | undefined) ?? value.source.question,
    consistency:
      (stored?.final_answer_consistency as string | undefined) ?? candidate.answer_consistency,
    contextRefs: (
      (stored?.final_context_refs as string[] | undefined) ??
      candidate.recommended_context_refs
    ).join(" / "),
    revisedAnswer:
      (stored?.revised_answer as string | undefined) ?? candidate.revised_answer,
    reviewer,
    note: value.review.note ?? "",
  };
}

function parseRefs(value: string): string[] {
  return value
    .split(/[\s,，/]+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function toReviewPatch(value: unknown): ReviewPatch {
  const draft = requireFidicRagDraft(value);
  return {
    status: draft.status,
    values: {
      final_task_type: draft.taskType,
      final_question_quality: draft.questionQuality,
      revised_question: draft.revisedQuestion,
      final_answer_consistency: draft.consistency,
      final_context_refs: parseRefs(draft.contextRefs),
      revised_answer: draft.revisedAnswer,
      reviewer: draft.reviewer,
    },
    note: draft.note,
  };
}

export const fidicRagTaskPlugin: TaskPlugin = {
  key: "fidic_rag",
  createDraft,
  toReviewPatch,
  onSaved(value) {
    const draft = requireFidicRagDraft(value);
    window.localStorage.setItem("review-workspace.reviewer", draft.reviewer);
  },
  View: FidicRagView,
};
