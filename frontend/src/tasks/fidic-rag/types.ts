import type { ReviewItem, ReviewRecord } from "../../types";

export type ContextAssessment = {
  suggested_task_type: string;
  question_quality: string;
  question_issues: string[];
  recommended_context_refs: string[];
  answer_consistency: string;
  revised_answer: string;
  answer_issues: string[];
  human_review_priority: string;
  overall_confidence: number;
  rationale: string;
};

export type ClauseContext = {
  context_id: string;
  covered_clause_nums: string[];
  metadata: {
    title_cn?: string;
    title_en?: string;
    pages?: number[];
    context_scope?: string;
  };
  text_cn: string;
  text_en: string;
};

export type FidicRagItem = ReviewItem & {
  source: {
    question: string;
    existing_answer: string;
    clause_contexts: ClauseContext[];
  };
  prediction: {
    context_audit: ContextAssessment;
    audit_meta: {
      audit_version: string;
      model: { provider: string; name: string; system_fingerprint?: string };
      attempt_count: number;
    };
  };
  review: Partial<ReviewRecord>;
  metadata: {
    pilot_index: number;
    pilot_stratum: string;
  };
};

export type FidicRagDraft = {
  status: string;
  taskType: string;
  questionQuality: string;
  revisedQuestion: string;
  consistency: string;
  contextRefs: string;
  revisedAnswer: string;
  reviewer: string;
  note: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function requireFidicRagItem(item: ReviewItem): FidicRagItem {
  const source = item.source;
  const prediction = item.prediction;
  const metadata = item.metadata;
  if (
    typeof source.question !== "string" ||
    typeof source.existing_answer !== "string" ||
    !Array.isArray(source.clause_contexts) ||
    !isRecord(prediction.context_audit) ||
    typeof metadata.pilot_index !== "number"
  ) {
    throw new Error(`Invalid FIDIC RAG item: ${item.id}`);
  }
  return item as FidicRagItem;
}

export function requireFidicRagDraft(draft: unknown): FidicRagDraft {
  if (
    !isRecord(draft) ||
    typeof draft.status !== "string" ||
    typeof draft.taskType !== "string" ||
    typeof draft.questionQuality !== "string" ||
    typeof draft.revisedQuestion !== "string" ||
    typeof draft.consistency !== "string" ||
    typeof draft.contextRefs !== "string" ||
    typeof draft.revisedAnswer !== "string" ||
    typeof draft.reviewer !== "string" ||
    typeof draft.note !== "string"
  ) {
    throw new Error("Invalid FIDIC RAG review draft");
  }
  return draft as FidicRagDraft;
}
