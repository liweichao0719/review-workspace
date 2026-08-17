import type { ReviewItem, ReviewPatch } from "../../types";
import type { TaskPlugin } from "../types";
import { ArticleReviewView } from "./ArticleReviewView";
import {
  requireArticleReviewDraft,
  requireArticleReviewItem,
  type ArticleReviewDraft,
} from "./types";

function defaultRelevance(decision: string, confidence: number): string {
  if (decision === "exclude") return "irrelevant";
  if (decision === "needs_followup") return "low";
  return confidence >= 0.9 ? "high" : "medium";
}

function createDraft(item: ReviewItem): ArticleReviewDraft {
  const value = requireArticleReviewItem(item);
  const suggestion = value.prediction.article_triage;
  const stored = value.review.values as Record<string, unknown> | undefined;
  const tags =
    (stored?.final_tags as string[] | undefined) ?? suggestion.suggested_tags;
  return {
    status: value.status || "pending",
    decision: (stored?.decision as string | undefined) ?? suggestion.decision,
    relevance:
      (stored?.relevance as string | undefined) ??
      defaultRelevance(suggestion.decision, suggestion.confidence),
    tagsText: tags.join(" / "),
    evidenceQuote: (stored?.evidence_quote as string | undefined) ?? "",
    decisionReason:
      (stored?.decision_reason as string | undefined) ?? suggestion.reason,
    reviewer:
      (stored?.reviewer as string | undefined) ??
      window.localStorage.getItem("review-workspace.reviewer") ??
      "",
    note: value.review.note ?? "",
  };
}

function parseTags(value: string): string[] {
  return value
    .split(/[\n,，/]+/)
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function toReviewPatch(value: unknown): ReviewPatch {
  const draft = requireArticleReviewDraft(value);
  return {
    status: draft.status,
    values: {
      decision: draft.decision,
      relevance: draft.relevance,
      final_tags: parseTags(draft.tagsText),
      evidence_quote: draft.evidenceQuote,
      decision_reason: draft.decisionReason,
      reviewer: draft.reviewer,
    },
    note: draft.note,
  };
}

export const articleReviewTaskPlugin: TaskPlugin = {
  key: "article_review",
  createDraft,
  toReviewPatch,
  onSaved(value) {
    const draft = requireArticleReviewDraft(value);
    window.localStorage.setItem("review-workspace.reviewer", draft.reviewer);
  },
  View: ArticleReviewView,
};
