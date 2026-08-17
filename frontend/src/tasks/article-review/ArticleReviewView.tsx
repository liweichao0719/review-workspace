import type { TaskViewProps } from "../types";
import {
  requireArticleReviewDraft,
  requireArticleReviewItem,
  type ArticleReviewDraft,
} from "./types";

const DECISION_LABELS: Record<string, string> = {
  include: "收录",
  exclude: "排除",
  needs_followup: "需要核查",
};

const RELEVANCE_LABELS: Record<string, string> = {
  high: "高度相关",
  medium: "中度相关",
  low: "低度相关",
  irrelevant: "不相关",
};

export function ArticleReviewView({
  item: rawItem,
  draft: rawDraft,
  task,
  datasetVersion,
  saveState,
  canMovePrevious,
  canMoveNext,
  onDraftChange,
  onMove,
}: TaskViewProps) {
  const item = requireArticleReviewItem(rawItem);
  const draft = requireArticleReviewDraft(rawDraft);
  const suggestion = item.prediction.article_triage;

  const updateDraft = <K extends keyof ArticleReviewDraft>(
    key: K,
    value: ArticleReviewDraft[K],
  ) => {
    onDraftChange({ ...draft, [key]: value });
  };

  return (
    <>
      <div className="review-header">
        <div>
          <div className="review-id">
            {item.id} · 示例文章 #{item.metadata.position}
            <span>合成数据</span>
          </div>
          <h2>{item.source.title}</h2>
        </div>
        <div className="nav-buttons">
          <button disabled={!canMovePrevious} onClick={() => onMove(-1)}>上一篇</button>
          <button disabled={!canMoveNext} onClick={() => onMove(1)}>下一篇</button>
        </div>
      </div>

      <div className="detail-layout">
        <div className="evidence-column">
          <section className="content-card article-body-card">
            <div className="section-title">
              <span>01 文章正文</span>
              <small>{item.source.language}</small>
            </div>
            <div className="article-meta">
              <span>{item.source.source_name}</span>
              <span>{item.source.published_at}</span>
              <span>数据版本 {datasetVersion || "—"}</span>
            </div>
            <p className="article-body">{item.source.body}</p>
            <div className="ref-row">
              {item.source.topics.map((topic) => (
                <span className="ref-chip" key={topic}>{topic}</span>
              ))}
            </div>
          </section>

          <section>
            <div className="section-heading">
              <div><span>02</span><h2>模型建议</h2></div>
              <p>仅供人工参考</p>
            </div>
            <article className="assessment-card article-suggestion">
              <div className="assessment-head">
                <div>
                  <h3>{DECISION_LABELS[suggestion.decision] ?? suggestion.decision}</h3>
                  <small>置信度 {(suggestion.confidence * 100).toFixed(0)}%</small>
                </div>
                <span className="priority">模型建议</span>
              </div>
              <p className="rationale">{suggestion.reason}</p>
              <div className="ref-row">
                {suggestion.suggested_tags.map((tag) => (
                  <span className="ref-chip" key={tag}>{tag}</span>
                ))}
              </div>
            </article>
          </section>
        </div>

        <aside className="decision-panel" data-testid="article-review-form">
          <div className="decision-title">
            <div>
              <span>文章审查</span>
              <small>专属字段由文章任务组件解释</small>
            </div>
            {item.review.revision && <i>修订 #{item.review.revision}</i>}
          </div>
          <label>
            <span>审核状态</span>
            <select
              value={draft.status}
              onChange={(event) => updateDraft("status", event.target.value)}
            >
              {task.statuses.map((option) => (
                <option value={option.value} key={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>最终决定</span>
            <select
              value={draft.decision}
              onChange={(event) => updateDraft("decision", event.target.value)}
            >
              {Object.entries(DECISION_LABELS).map(([value, label]) => (
                <option value={value} key={value}>{label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>相关性</span>
            <select
              value={draft.relevance}
              onChange={(event) => updateDraft("relevance", event.target.value)}
            >
              {Object.entries(RELEVANCE_LABELS).map(([value, label]) => (
                <option value={value} key={value}>{label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>最终标签</span>
            <input
              value={draft.tagsText}
              onChange={(event) => updateDraft("tagsText", event.target.value)}
              placeholder="供应链 / 物流"
            />
            <small>使用逗号或斜杠分隔，最多 8 个。</small>
          </label>
          <label>
            <span>证据摘录</span>
            <textarea
              value={draft.evidenceQuote}
              onChange={(event) => updateDraft("evidenceQuote", event.target.value)}
              rows={5}
              placeholder="从正文复制一段原文"
            />
            <small>收录文章必须填写，且需要与正文逐字一致。</small>
          </label>
          <label>
            <span>决定理由</span>
            <textarea
              value={draft.decisionReason}
              onChange={(event) => updateDraft("decisionReason", event.target.value)}
              rows={4}
            />
          </label>
          <label>
            <span>审核人</span>
            <input
              value={draft.reviewer}
              onChange={(event) => updateDraft("reviewer", event.target.value)}
              placeholder="姓名或代号"
            />
          </label>
          <label>
            <span>审核备注</span>
            <textarea
              value={draft.note}
              onChange={(event) => updateDraft("note", event.target.value)}
              rows={4}
            />
          </label>
          <div className="decision-foot">
            <span className={`save-state ${saveState}`}>
              {saveState === "saving"
                ? "保存中"
                : saveState === "error"
                  ? "保存失败"
                  : saveState === "saved"
                    ? "已保存"
                    : "尚未修改"}
            </span>
            <small>↑ ↓ 切换文章</small>
          </div>
        </aside>
      </div>
    </>
  );
}
