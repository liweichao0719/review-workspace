import { useEffect, useState } from "react";

import type { TaskViewProps } from "../types";
import {
  requireGraphReviewDraft,
  requireGraphReviewItem,
  type GraphEdge,
  type GraphNode,
  type GraphReviewDraft,
} from "./types";

const NODE_LABELS: Record<string, string> = {
  risk_event: "风险事件",
  vulnerability: "脆弱点",
  control: "控制措施",
  impact: "影响",
};

const EDGE_LABELS: Record<string, string> = {
  causes: "导致",
  contributes_to: "促成",
  mitigates: "缓解",
  indicates: "指示",
};

function nextIdentifier(prefix: string, used: string[]): string {
  const existing = new Set(used);
  let number = 1;
  while (existing.has(`${prefix}${number}`)) number += 1;
  return `${prefix}${number}`;
}

function evidenceError(evidence: string, sourceText: string): string {
  if (!evidence.trim()) return "请填写证据原文。";
  if (!sourceText.includes(evidence.trim())) return "证据必须与原文逐字一致。";
  return "";
}

type NodeEditorProps = {
  node: GraphNode;
  sourceText: string;
  canDelete: boolean;
  onApply: (node: GraphNode) => void;
  onDelete: () => void;
};

function NodeEditor({
  node,
  sourceText,
  canDelete,
  onApply,
  onDelete,
}: NodeEditorProps) {
  const [type, setType] = useState(node.type);
  const [label, setLabel] = useState(node.label);
  const [evidence, setEvidence] = useState(node.evidence);
  const [error, setError] = useState("");

  useEffect(() => {
    setType(node.type);
    setLabel(node.label);
    setEvidence(node.evidence);
    setError("");
  }, [node.type, node.label, node.evidence]);

  const apply = () => {
    if (!label.trim()) {
      setError("节点名称不能为空。");
      return;
    }
    const nextError = evidenceError(evidence, sourceText);
    if (nextError) {
      setError(nextError);
      return;
    }
    onApply({
      id: node.id,
      type,
      label: label.trim(),
      evidence: evidence.trim(),
    });
    setError("");
  };

  return (
    <article className="graph-edit-row graph-node-row" data-node-id={node.id}>
      <div className="graph-row-head">
        <div><code>{node.id}</code><strong>{NODE_LABELS[type] ?? type}</strong></div>
        <div className="graph-row-actions">
          <button type="button" onClick={apply}>应用修改</button>
          <button
            type="button"
            className="danger"
            disabled={!canDelete}
            title={canDelete ? "删除节点及其关联关系" : "图中至少保留一个节点"}
            onClick={onDelete}
          >删除</button>
        </div>
      </div>
      <div className="graph-fields node-fields">
        <label>
          <span>节点类型</span>
          <select value={type} onChange={(event) => setType(event.target.value)}>
            {Object.entries(NODE_LABELS).map(([value, text]) => (
              <option value={value} key={value}>{text}</option>
            ))}
          </select>
        </label>
        <label>
          <span>节点名称</span>
          <input value={label} onChange={(event) => setLabel(event.target.value)} />
        </label>
      </div>
      <label>
        <span>证据原文</span>
        <textarea
          rows={2}
          value={evidence}
          onChange={(event) => setEvidence(event.target.value)}
        />
      </label>
      {error && <p className="graph-field-error">{error}</p>}
    </article>
  );
}

type EdgeEditorProps = {
  edge: GraphEdge;
  nodes: GraphNode[];
  sourceText: string;
  onApply: (edge: GraphEdge) => void;
  onDelete: () => void;
};

function EdgeEditor({
  edge,
  nodes,
  sourceText,
  onApply,
  onDelete,
}: EdgeEditorProps) {
  const [source, setSource] = useState(edge.source);
  const [target, setTarget] = useState(edge.target);
  const [type, setType] = useState(edge.type);
  const [evidence, setEvidence] = useState(edge.evidence);
  const [error, setError] = useState("");

  useEffect(() => {
    setSource(edge.source);
    setTarget(edge.target);
    setType(edge.type);
    setEvidence(edge.evidence);
    setError("");
  }, [edge.source, edge.target, edge.type, edge.evidence]);

  const apply = () => {
    if (source === target) {
      setError("关系不能连接节点自身。");
      return;
    }
    const nextError = evidenceError(evidence, sourceText);
    if (nextError) {
      setError(nextError);
      return;
    }
    onApply({
      id: edge.id,
      source,
      target,
      type,
      evidence: evidence.trim(),
    });
    setError("");
  };

  return (
    <article className="graph-edit-row graph-edge-row" data-edge-id={edge.id}>
      <div className="graph-row-head">
        <div><code>{edge.id}</code><strong>{EDGE_LABELS[type] ?? type}</strong></div>
        <div className="graph-row-actions">
          <button type="button" onClick={apply}>应用修改</button>
          <button type="button" className="danger" onClick={onDelete}>删除</button>
        </div>
      </div>
      <div className="graph-fields edge-fields">
        <label>
          <span>起点</span>
          <select value={source} onChange={(event) => setSource(event.target.value)}>
            {nodes.map((node) => (
              <option value={node.id} key={node.id}>{node.id} · {node.label}</option>
            ))}
          </select>
        </label>
        <label>
          <span>关系</span>
          <select value={type} onChange={(event) => setType(event.target.value)}>
            {Object.entries(EDGE_LABELS).map(([value, text]) => (
              <option value={value} key={value}>{text}</option>
            ))}
          </select>
        </label>
        <label>
          <span>终点</span>
          <select value={target} onChange={(event) => setTarget(event.target.value)}>
            {nodes.map((node) => (
              <option value={node.id} key={node.id}>{node.id} · {node.label}</option>
            ))}
          </select>
        </label>
      </div>
      <label>
        <span>证据原文</span>
        <textarea
          rows={2}
          value={evidence}
          onChange={(event) => setEvidence(event.target.value)}
        />
      </label>
      {error && <p className="graph-field-error">{error}</p>}
    </article>
  );
}

type AddNodeFormProps = {
  nextId: string;
  sourceText: string;
  onAdd: (node: GraphNode) => void;
};

function AddNodeForm({ nextId, sourceText, onAdd }: AddNodeFormProps) {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState("risk_event");
  const [label, setLabel] = useState("");
  const [evidence, setEvidence] = useState("");
  const [error, setError] = useState("");

  const add = () => {
    if (!label.trim()) {
      setError("节点名称不能为空。");
      return;
    }
    const nextError = evidenceError(evidence, sourceText);
    if (nextError) {
      setError(nextError);
      return;
    }
    onAdd({ id: nextId, type, label: label.trim(), evidence: evidence.trim() });
    setLabel("");
    setEvidence("");
    setError("");
    setOpen(false);
  };

  if (!open) {
    return <button type="button" className="graph-add-button" onClick={() => setOpen(true)}>+ 新增节点</button>;
  }
  return (
    <article className="graph-edit-row graph-add-form" data-testid="add-node-form">
      <div className="graph-row-head"><div><code>{nextId}</code><strong>新增节点</strong></div></div>
      <div className="graph-fields node-fields">
        <label>
          <span>节点类型</span>
          <select value={type} onChange={(event) => setType(event.target.value)}>
            {Object.entries(NODE_LABELS).map(([value, text]) => (
              <option value={value} key={value}>{text}</option>
            ))}
          </select>
        </label>
        <label>
          <span>节点名称</span>
          <input value={label} onChange={(event) => setLabel(event.target.value)} />
        </label>
      </div>
      <label>
        <span>证据原文</span>
        <textarea rows={2} value={evidence} onChange={(event) => setEvidence(event.target.value)} />
      </label>
      {error && <p className="graph-field-error">{error}</p>}
      <div className="graph-form-actions">
        <button type="button" onClick={add}>添加</button>
        <button type="button" className="secondary" onClick={() => setOpen(false)}>取消</button>
      </div>
    </article>
  );
}

type AddEdgeFormProps = {
  nextId: string;
  nodes: GraphNode[];
  sourceText: string;
  onAdd: (edge: GraphEdge) => void;
};

function AddEdgeForm({ nextId, nodes, sourceText, onAdd }: AddEdgeFormProps) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState(nodes[0]?.id ?? "");
  const [target, setTarget] = useState(nodes[1]?.id ?? "");
  const [type, setType] = useState("causes");
  const [evidence, setEvidence] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!nodes.some((node) => node.id === source)) setSource(nodes[0]?.id ?? "");
    if (!nodes.some((node) => node.id === target)) setTarget(nodes[1]?.id ?? "");
  }, [nodes, source, target]);

  const add = () => {
    if (source === target) {
      setError("关系不能连接节点自身。");
      return;
    }
    const nextError = evidenceError(evidence, sourceText);
    if (nextError) {
      setError(nextError);
      return;
    }
    onAdd({ id: nextId, source, target, type, evidence: evidence.trim() });
    setEvidence("");
    setError("");
    setOpen(false);
  };

  if (nodes.length < 2) {
    return <p className="graph-form-hint">至少需要两个节点才能新增关系。</p>;
  }
  if (!open) {
    return <button type="button" className="graph-add-button" onClick={() => setOpen(true)}>+ 新增关系</button>;
  }
  return (
    <article className="graph-edit-row graph-add-form" data-testid="add-edge-form">
      <div className="graph-row-head"><div><code>{nextId}</code><strong>新增关系</strong></div></div>
      <div className="graph-fields edge-fields">
        <label>
          <span>起点</span>
          <select value={source} onChange={(event) => setSource(event.target.value)}>
            {nodes.map((node) => <option value={node.id} key={node.id}>{node.id} · {node.label}</option>)}
          </select>
        </label>
        <label>
          <span>关系</span>
          <select value={type} onChange={(event) => setType(event.target.value)}>
            {Object.entries(EDGE_LABELS).map(([value, text]) => (
              <option value={value} key={value}>{text}</option>
            ))}
          </select>
        </label>
        <label>
          <span>终点</span>
          <select value={target} onChange={(event) => setTarget(event.target.value)}>
            {nodes.map((node) => <option value={node.id} key={node.id}>{node.id} · {node.label}</option>)}
          </select>
        </label>
      </div>
      <label>
        <span>证据原文</span>
        <textarea rows={2} value={evidence} onChange={(event) => setEvidence(event.target.value)} />
      </label>
      {error && <p className="graph-field-error">{error}</p>}
      <div className="graph-form-actions">
        <button type="button" onClick={add}>添加</button>
        <button type="button" className="secondary" onClick={() => setOpen(false)}>取消</button>
      </div>
    </article>
  );
}

function saveStateLabel(saveState: TaskViewProps["saveState"]): string {
  if (saveState === "saving") return "保存中";
  if (saveState === "error") return "保存失败";
  if (saveState === "saved") return "已保存";
  return "尚未修改";
}

export function GraphReviewView({
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
  const item = requireGraphReviewItem(rawItem);
  const draft = requireGraphReviewDraft(rawDraft);
  const candidate = item.prediction.graph_candidate;

  const updateDraft = <K extends keyof GraphReviewDraft>(
    key: K,
    value: GraphReviewDraft[K],
  ) => onDraftChange({ ...draft, [key]: value });

  const deleteNode = (nodeId: string) => {
    if (draft.nodes.length <= 1) return;
    if (!window.confirm("删除该节点并同时移除所有关联关系？")) return;
    onDraftChange({
      ...draft,
      nodes: draft.nodes.filter((node) => node.id !== nodeId),
      edges: draft.edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId,
      ),
    });
  };

  return (
    <>
      <div className="review-header">
        <div>
          <div className="review-id">
            {item.id} · 合成图 #{item.metadata.position}
            <span>合成数据</span>
          </div>
          <h2>{item.source.title}</h2>
        </div>
        <div className="nav-buttons">
          <button disabled={!canMovePrevious} onClick={() => onMove(-1)}>上一条</button>
          <button disabled={!canMoveNext} onClick={() => onMove(1)}>下一条</button>
        </div>
      </div>

      <div className="graph-review-layout">
        <div className="graph-source-column">
          <section className="content-card graph-source-card">
            <div className="section-title">
              <span>01 证据原文</span>
              <small>{item.source.language}</small>
            </div>
            <div className="article-meta">
              <span>{item.source.source_name}</span>
              <span>{item.source.published_at}</span>
              <span>版本 {datasetVersion || "—"}</span>
            </div>
            <p>{item.source.text}</p>
            <small className="graph-source-tip">节点和关系的证据都必须从此处逐字复制。</small>
          </section>

          <section className="content-card graph-candidate-card">
            <div className="section-title">
              <span>02 模型初始结构</span>
              <small>仅供参考</small>
            </div>
            <div className="graph-candidate-stats">
              <strong>{candidate.nodes.length}<small>节点</small></strong>
              <strong>{candidate.edges.length}<small>关系</small></strong>
            </div>
            <div className="graph-candidate-list">
              {candidate.nodes.map((node) => (
                <div key={node.id}>
                  <code>{node.id}</code>
                  <span>{node.label}</span>
                  <small>{NODE_LABELS[node.type] ?? node.type}</small>
                </div>
              ))}
            </div>
            <div className="graph-candidate-edges">
              {candidate.edges.map((edge) => (
                <span key={edge.id}>
                  {edge.source} → {EDGE_LABELS[edge.type] ?? edge.type} → {edge.target}
                </span>
              ))}
            </div>
          </section>
        </div>

        <div className="graph-editor-column">
          <section className="content-card graph-review-meta" data-testid="graph-review-form">
            <div className="decision-title">
              <div>
                <span>结构化图复核</span>
                <small>增删改以完整图为单位自动保存</small>
              </div>
              {item.review.revision && <i>修订 #{item.review.revision}</i>}
            </div>
            <div className="graph-meta-fields">
              <label>
                <span>审核状态</span>
                <select value={draft.status} onChange={(event) => updateDraft("status", event.target.value)}>
                  {task.statuses.map((option) => (
                    <option value={option.value} key={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>审核人</span>
                <input
                  value={draft.reviewer}
                  onChange={(event) => updateDraft("reviewer", event.target.value)}
                  placeholder="姓名或代号"
                />
              </label>
            </div>
            <label>
              <span>审核备注</span>
              <textarea rows={2} value={draft.note} onChange={(event) => updateDraft("note", event.target.value)} />
            </label>
            <div className="decision-foot">
              <span className={`save-state ${saveState}`}>{saveStateLabel(saveState)}</span>
              <small>{draft.nodes.length} 节点 · {draft.edges.length} 关系</small>
            </div>
          </section>

          <section className="graph-editor-section">
            <div className="graph-section-heading">
              <div><span>03</span><h2>最终节点</h2></div>
              <p>标识固定；修改后点击应用</p>
            </div>
            <div className="graph-edit-list">
              {draft.nodes.map((node) => (
                <NodeEditor
                  key={node.id}
                  node={node}
                  sourceText={item.source.text}
                  canDelete={draft.nodes.length > 1}
                  onApply={(nextNode) => updateDraft(
                    "nodes",
                    draft.nodes.map((value) => value.id === node.id ? nextNode : value),
                  )}
                  onDelete={() => deleteNode(node.id)}
                />
              ))}
              <AddNodeForm
                nextId={nextIdentifier("n", draft.nodes.map((node) => node.id))}
                sourceText={item.source.text}
                onAdd={(node) => updateDraft("nodes", [...draft.nodes, node])}
              />
            </div>
          </section>

          <section className="graph-editor-section">
            <div className="graph-section-heading">
              <div><span>04</span><h2>最终关系</h2></div>
              <p>端点必须引用现有节点</p>
            </div>
            <div className="graph-edit-list">
              {draft.edges.map((edge) => (
                <EdgeEditor
                  key={edge.id}
                  edge={edge}
                  nodes={draft.nodes}
                  sourceText={item.source.text}
                  onApply={(nextEdge) => updateDraft(
                    "edges",
                    draft.edges.map((value) => value.id === edge.id ? nextEdge : value),
                  )}
                  onDelete={() => updateDraft(
                    "edges",
                    draft.edges.filter((value) => value.id !== edge.id),
                  )}
                />
              ))}
              <AddEdgeForm
                nextId={nextIdentifier("e", draft.edges.map((edge) => edge.id))}
                nodes={draft.nodes}
                sourceText={item.source.text}
                onAdd={(edge) => updateDraft("edges", [...draft.edges, edge])}
              />
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
