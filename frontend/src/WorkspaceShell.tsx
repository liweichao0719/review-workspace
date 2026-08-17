import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { exportUrl, getItem, getItems, getProjects, saveReview } from "./api";
import { EmptyState } from "./components/EmptyState";
import { getTaskPlugin } from "./tasks/registry";
import type {
  Project,
  ProjectTask,
  ReviewItem,
  ReviewListResponse,
  SaveState,
} from "./types";

function serializeDraft(draft: unknown): string {
  return JSON.stringify(draft) ?? "null";
}

export function WorkspaceShell() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [task, setTask] = useState<ProjectTask | null>(null);
  const [list, setList] = useState<ReviewListResponse | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [item, setItem] = useState<ReviewItem | null>(null);
  const [draft, setDraft] = useState<unknown | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [error, setError] = useState("");
  const [loadingItem, setLoadingItem] = useState(false);
  const baseline = useRef("");
  const requestSequence = useRef(0);

  const taskPlugin = useMemo(
    () => (task ? getTaskPlugin(task.renderer_key) : undefined),
    [task],
  );
  const statusLabels = useMemo(
    () => Object.fromEntries(
      (task?.statuses ?? []).map((status) => [status.value, status.label]),
    ) as Record<string, string>,
    [task],
  );

  useEffect(() => {
    getProjects()
      .then((values) => {
        setProjects(values);
        if (values[0]) {
          setProject(values[0]);
          setTask(values[0].tasks[0] ?? null);
        }
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  const loadList = useCallback(async () => {
    if (!project || !task) return;
    try {
      const response = await getItems(project.id, task.id, query, statusFilter);
      setList(response);
      setSelectedId((current) => {
        if (current && response.items.some((entry) => entry.id === current)) {
          return current;
        }
        return response.items[0]?.id ?? "";
      });
    } catch (reason) {
      setError((reason as Error).message);
    }
  }, [project, task, query, statusFilter]);

  useEffect(() => {
    const timeout = window.setTimeout(loadList, 220);
    return () => window.clearTimeout(timeout);
  }, [loadList]);

  useEffect(() => {
    if (!project || !task || !taskPlugin || !selectedId) {
      setItem(null);
      setDraft(null);
      return;
    }
    const sequence = ++requestSequence.current;
    setLoadingItem(true);
    getItem(project.id, task.id, selectedId)
      .then((value) => {
        if (sequence !== requestSequence.current) return;
        const nextDraft = taskPlugin.createDraft(value);
        setItem(value);
        setDraft(nextDraft);
        baseline.current = serializeDraft(nextDraft);
        setSaveState("idle");
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => {
        if (sequence === requestSequence.current) setLoadingItem(false);
      });
  }, [project, task, taskPlugin, selectedId]);

  const persistCurrent = useCallback(async (): Promise<boolean> => {
    if (!project || !task || !taskPlugin || !item || draft === null) return true;
    const serialized = serializeDraft(draft);
    if (serialized === baseline.current) return true;
    setSaveState("saving");
    try {
      await saveReview(
        project.id,
        task.id,
        item.id,
        taskPlugin.toReviewPatch(draft),
      );
      const refreshed = await getItem(project.id, task.id, item.id);
      baseline.current = serialized;
      taskPlugin.onSaved?.(draft);
      setItem(refreshed);
      setSaveState("saved");
      await loadList();
      return true;
    } catch (reason) {
      setSaveState("error");
      setError((reason as Error).message);
      return false;
    }
  }, [draft, item, loadList, project, task, taskPlugin]);

  useEffect(() => {
    if (draft === null || serializeDraft(draft) === baseline.current) return;
    setSaveState("saving");
    const timeout = window.setTimeout(() => void persistCurrent(), 800);
    return () => window.clearTimeout(timeout);
  }, [draft, persistCurrent]);

  const selectedIndex = useMemo(
    () => list?.items.findIndex((entry) => entry.id === selectedId) ?? -1,
    [list, selectedId],
  );

  const selectItem = useCallback(async (nextId: string) => {
    if (!nextId || nextId === selectedId) return;
    if (await persistCurrent()) setSelectedId(nextId);
  }, [persistCurrent, selectedId]);

  const move = useCallback((offset: number) => {
    if (!list || selectedIndex < 0) return;
    const target = list.items[selectedIndex + offset];
    if (target) void selectItem(target.id);
  }, [list, selectedIndex, selectItem]);

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      const tag = (event.target as HTMLElement).tagName;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(tag)) return;
      if (event.key === "ArrowDown") move(1);
      if (event.key === "ArrowUp") move(-1);
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [move]);

  const completed = (list?.counts.total ?? 0) - (list?.counts.pending ?? 0);
  const progress = list?.counts.total
    ? Math.round((completed / list.counts.total) * 100)
    : 0;
  const TaskView = taskPlugin?.View;

  if (projects.length === 0 && !error) {
    return <EmptyState message="正在连接审查项目…" />;
  }

  return (
    <div className="workspace">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">RW</span>
          <div><p>AI DATA QUALITY</p><h1>Review Workspace</h1></div>
        </div>
        <div className="top-actions">
          <div className={`save-indicator ${saveState}`}>
            {saveState === "saving" && "正在保存…"}
            {saveState === "saved" && "已自动保存"}
            {saveState === "error" && "保存失败"}
            {saveState === "idle" && "修改后自动保存"}
          </div>
          {project && task && (
            <a className="export-button" href={exportUrl(project.id, task.id)}>
              导出 JSONL
            </a>
          )}
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError("")}>关闭</button>
        </div>
      )}

      <div className="workspace-grid">
        <aside className="sidebar">
          <div className="scope-selectors">
            <label>
              <span>项目</span>
              <select
                data-testid="project-select"
                value={project?.id ?? ""}
                onChange={(event) => {
                  const next = projects.find(
                    (value) => value.id === event.target.value,
                  ) ?? null;
                  setProject(next);
                  setTask(next?.tasks[0] ?? null);
                  setStatusFilter("all");
                }}
              >
                {projects.map((value) => (
                  <option key={value.id} value={value.id}>{value.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>审查任务</span>
              <select
                data-testid="task-select"
                value={task?.id ?? ""}
                onChange={(event) => {
                  setTask(
                    project?.tasks.find((value) => value.id === event.target.value) ?? null,
                  );
                  setStatusFilter("all");
                }}
              >
                {project?.tasks.map((value) => (
                  <option key={value.id} value={value.id}>{value.name}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="progress-block">
            <div>
              <strong>{completed}/{list?.counts.total ?? 0}</strong>
              <span>{progress}%</span>
            </div>
            <div className="progress-track">
              <i style={{ width: `${progress}%` }} />
            </div>
            <p>数据版本 {list?.dataset_version ?? "—"}</p>
          </div>
          <div className="filters">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索标题或 ID"
            />
            <div className="status-filters">
              {["all", ...(task?.statuses.map((value) => value.value) ?? [])].map(
                (value) => (
                  <button
                    className={statusFilter === value ? "active" : ""}
                    key={value}
                    onClick={() => setStatusFilter(value)}
                  >
                    {value === "all" ? "全部" : statusLabels[value] ?? value}
                    {value !== "all" && <small>{list?.counts[value] ?? 0}</small>}
                  </button>
                ),
              )}
            </div>
          </div>
          <div className="item-count">当前 {list?.total ?? 0} 条</div>
          <nav className="item-list">
            {list?.items.map((entry) => (
              <button
                className={`item-row ${entry.id === selectedId ? "selected" : ""}`}
                key={entry.id}
                onClick={() => void selectItem(entry.id)}
              >
                <div className="item-meta">
                  <span>{entry.id}</span>
                  <i
                    className={`status-dot status-${entry.status}`}
                    title={statusLabels[entry.status] ?? entry.status}
                  />
                </div>
                <strong>{entry.title}</strong>
                <div className="badges">
                  {entry.badges.map((badge) => <span key={badge}>{badge}</span>)}
                </div>
              </button>
            ))}
            {list?.items.length === 0 && (
              <EmptyState message="没有符合筛选条件的条目" />
            )}
          </nav>
        </aside>

        <main className="review-main">
          {loadingItem && <div className="loading-line" />}
          {task && !TaskView ? (
            <EmptyState message={`尚未注册任务组件：${task.renderer_key}`} />
          ) : !task || !item || draft === null || !TaskView ? (
            <EmptyState message="从左侧选择一条数据开始审查" />
          ) : (
            <TaskView
              item={item}
              draft={draft}
              task={task}
              datasetVersion={list?.dataset_version ?? ""}
              saveState={saveState}
              canMovePrevious={selectedIndex > 0}
              canMoveNext={Boolean(list && selectedIndex < list.items.length - 1)}
              onDraftChange={setDraft}
              onMove={move}
            />
          )}
        </main>
      </div>
    </div>
  );
}
