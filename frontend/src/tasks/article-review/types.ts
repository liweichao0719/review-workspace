import type { ReviewItem, ReviewRecord } from "../../types";

export type ArticleSuggestion = {
  decision: string;
  confidence: number;
  reason: string;
  suggested_tags: string[];
};

export type ArticleReviewItem = ReviewItem & {
  source: {
    title: string;
    body: string;
    source_name: string;
    published_at: string;
    language: string;
    topics: string[];
  };
  prediction: {
    article_triage: ArticleSuggestion;
  };
  review: Partial<ReviewRecord>;
  metadata: {
    position: number;
    synthetic: boolean;
  };
};

export type ArticleReviewDraft = {
  status: string;
  decision: string;
  relevance: string;
  tagsText: string;
  evidenceQuote: string;
  decisionReason: string;
  reviewer: string;
  note: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function requireArticleReviewItem(item: ReviewItem): ArticleReviewItem {
  const source = item.source;
  const prediction = item.prediction;
  const suggestion = prediction.article_triage;
  if (
    typeof source.title !== "string" ||
    typeof source.body !== "string" ||
    typeof source.source_name !== "string" ||
    typeof source.published_at !== "string" ||
    !Array.isArray(source.topics) ||
    !isRecord(suggestion) ||
    typeof suggestion.decision !== "string" ||
    typeof suggestion.confidence !== "number" ||
    typeof suggestion.reason !== "string" ||
    !Array.isArray(suggestion.suggested_tags) ||
    typeof item.metadata.position !== "number"
  ) {
    throw new Error(`Invalid article review item: ${item.id}`);
  }
  return item as ArticleReviewItem;
}

export function requireArticleReviewDraft(draft: unknown): ArticleReviewDraft {
  if (
    !isRecord(draft) ||
    typeof draft.status !== "string" ||
    typeof draft.decision !== "string" ||
    typeof draft.relevance !== "string" ||
    typeof draft.tagsText !== "string" ||
    typeof draft.evidenceQuote !== "string" ||
    typeof draft.decisionReason !== "string" ||
    typeof draft.reviewer !== "string" ||
    typeof draft.note !== "string"
  ) {
    throw new Error("Invalid article review draft");
  }
  return draft as ArticleReviewDraft;
}
