import { EmptyState } from "../../components/EmptyState";
import type { TaskViewProps } from "../types";
import {
  requireFidicRagDraft,
  requireFidicRagItem,
  type ContextAssessment,
  type FidicRagDraft,
} from "./types";

const TASK_LABELS: Record<string, string> = {
  yellowbook_qa: "黄皮书知识问答",
  scenario_analysis: "工程场景分析",
  special_clause_review: "专用条款审查",
  multi_clause_reasoning: "多条款推理",
  insufficient_evidence: "证据不足",
};

const QUALITY_LABELS: Record<string, string> = {
  usable: "问题可用",
  needs_revision: "问题需修改",
  unusable: "问题不可用",
};

const CONSISTENCY_LABELS: Record<string, string> = {
  supported: "完全支持",
  partially_supported: "部分支持",
  unsupported: "不支持",
  contradictory: "相互矛盾",
  insufficient_evidence: "证据不足",
};

function FrozenDatasetCard({
  value,
  contextCount,
}: {
  value: ContextAssessment;
  contextCount: number;
}) {
  return (
    <article className="assessment-card frozen-card">
      <div className="assessment-head">
        <div>
          <h3>冻结数据概览</h3>
          <small>这是当前开发集基线；右侧修订会单独保存，不会覆盖源数据。</small>
        </div>
        <span className={`priority priority-${value.human_review_priority}`}>冻结</span>
      </div>
      <dl className="facts frozen-facts">
        <div>
          <dt>题型</dt>
          <dd>{TASK_LABELS[value.suggested_task_type] ?? value.suggested_task_type}</dd>
        </div>
        <div>
          <dt>问题质量</dt>
          <dd>{QUALITY_LABELS[value.question_quality] ?? value.question_quality}</dd>
        </div>
        <div>
          <dt>上下文</dt>
          <dd>{contextCount} 个证据块</dd>
        </div>
      </dl>
      <div className="ref-row">
        {value.recommended_context_refs.length ? (
          value.recommended_context_refs.map((ref) => (
            <span className="ref-chip" key={ref}>{ref}</span>
          ))
        ) : (
          <span className="muted">证据不足题不选择上下文</span>
        )}
      </div>
      <p className="rationale">
        审查时只判断题型、问题、标准答案和下方完整双语上下文是否仍然一致。
      </p>
    </article>
  );
}

export function FidicRagView({
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
  const item = requireFidicRagItem(rawItem);
  const draft = requireFidicRagDraft(rawDraft);

  const updateDraft = <K extends keyof FidicRagDraft>(
    key: K,
    value: FidicRagDraft[K],
  ) => {
    onDraftChange({ ...draft, [key]: value });
  };

  return (
    <>
      <div className="review-header">
        <div>
          <div className="review-id">
            {item.id} · 开发集 #{item.metadata.pilot_index}
          </div>
          <h2>{item.source.question}</h2>
        </div>
        <div className="nav-buttons">
          <button disabled={!canMovePrevious} onClick={() => onMove(-1)}>上一题</button>
          <button disabled={!canMoveNext} onClick={() => onMove(1)}>下一题</button>
        </div>
      </div>

      <div className="detail-layout">
        <div className="evidence-column">
          <section className="content-card answer-card">
            <div className="section-title">
              <span>01 标准答案</span>
              <small>冻结版本</small>
            </div>
            <p>{item.source.existing_answer}</p>
          </section>

          <section>
            <div className="section-heading">
              <div><span>02</span><h2>冻结数据概览</h2></div>
              <p>数据版本 {datasetVersion || "—"}</p>
            </div>
            <FrozenDatasetCard
              value={item.prediction.context_audit}
              contextCount={item.source.clause_contexts.length}
            />
          </section>

          <section>
            <div className="section-heading">
              <div><span>03</span><h2>上下文条款</h2></div>
              <p>{item.source.clause_contexts.length} 个证据块</p>
            </div>
            <div className="clause-stack">
              {item.source.clause_contexts.map((context) => {
                const ref = context.context_id.split(":").at(-1) ?? context.context_id;
                return (
                  <details
                    className="clause-card"
                    key={context.context_id}
                    open={item.source.clause_contexts.length <= 3}
                  >
                    <summary>
                      <div>
                        <strong>{ref}</strong>
                        <span>{context.metadata.title_cn || context.metadata.title_en}</span>
                      </div>
                      <small>
                        {context.metadata.pages?.length
                          ? `第 ${context.metadata.pages.join("–")} 页`
                          : ""}
                      </small>
                    </summary>
                    <div className="bilingual">
                      <div><label>中文</label><p>{context.text_cn}</p></div>
                      <div><label>English</label><p>{context.text_en}</p></div>
                    </div>
                  </details>
                );
              })}
              {item.source.clause_contexts.length === 0 && (
                <EmptyState message="该候选未选择上下文；请先判断问题是否缺少必要信息" />
              )}
            </div>
          </section>
        </div>

        <aside className="decision-panel">
          <div className="decision-title">
            <div>
              <span>独立审查修订</span>
              <small>保存为新版本记录，不会修改冻结开发集</small>
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
            <span>最终题型</span>
            <select
              value={draft.taskType}
              onChange={(event) => updateDraft("taskType", event.target.value)}
            >
              {Object.entries(TASK_LABELS).map(([value, label]) => (
                <option value={value} key={value}>{label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>问题质量</span>
            <select
              value={draft.questionQuality}
              onChange={(event) => updateDraft("questionQuality", event.target.value)}
            >
              {Object.entries(QUALITY_LABELS).map(([value, label]) => (
                <option value={value} key={value}>{label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>最终问题</span>
            <textarea
              value={draft.revisedQuestion}
              onChange={(event) => updateDraft("revisedQuestion", event.target.value)}
              rows={4}
            />
          </label>
          <label>
            <span>答案一致性</span>
            <select
              value={draft.consistency}
              onChange={(event) => updateDraft("consistency", event.target.value)}
            >
              {Object.entries(CONSISTENCY_LABELS).map(([value, label]) => (
                <option value={value} key={value}>{label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>最终上下文条款</span>
            <input
              value={draft.contextRefs}
              onChange={(event) => updateDraft("contextRefs", event.target.value)}
              placeholder="5.1 / 5.2 / 8.5"
            />
            <small>填写完整证据块编号，不是检索子条款。</small>
          </label>
          <label>
            <span>最终答案</span>
            <textarea
              value={draft.revisedAnswer}
              onChange={(event) => updateDraft("revisedAnswer", event.target.value)}
              rows={12}
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
              rows={6}
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
            <small>↑ ↓ 切换题目</small>
          </div>
        </aside>
      </div>
    </>
  );
}
