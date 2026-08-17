import { articleReviewTaskPlugin } from "./article-review/plugin";
import { fidicRagTaskPlugin } from "./fidic-rag/plugin";
import type { TaskPlugin } from "./types";

const plugins = new Map<string, TaskPlugin>();

export function registerTaskPlugin(plugin: TaskPlugin): void {
  if (plugins.has(plugin.key)) {
    throw new Error(`Task renderer already registered: ${plugin.key}`);
  }
  plugins.set(plugin.key, plugin);
}

export function getTaskPlugin(rendererKey: string): TaskPlugin | undefined {
  return plugins.get(rendererKey);
}

registerTaskPlugin(articleReviewTaskPlugin);
registerTaskPlugin(fidicRagTaskPlugin);
