import { readFileSync } from "node:fs";

import { expect, test, type Download, type Page } from "@playwright/test";


type ExportRow = {
  item_id: string;
  revision: number;
  status: string;
  values: Record<string, unknown>;
  note: string;
};

test.describe.configure({ mode: "serial" });

async function selectProject(
  page: Page,
  projectId: string,
  expectedTitle: string,
): Promise<void> {
  await page.getByTestId("project-select").selectOption(projectId);
  await expect(
    page.getByRole("heading", { level: 2, name: expectedTitle, exact: true }),
  ).toBeVisible();
}

async function waitForSaved(page: Page): Promise<void> {
  await expect(page.locator(".save-state")).toHaveText("已保存", {
    timeout: 12_000,
  });
}

async function downloadText(download: Download): Promise<string> {
  const path = await download.path();
  if (!path) throw new Error("download did not produce a local file");
  return readFileSync(path, "utf-8");
}

function parseExport(content: string): ExportRow[] {
  return content
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line) as ExportRow);
}

test("article review autosaves, survives reload, and exports", async ({ page }) => {
  await page.goto("/");
  await selectProject(page, "demo_articles", "东部港口调整夜间作业安排");

  const form = page.getByTestId("article-review-form");
  await form
    .getByLabel("证据摘录")
    .fill("东部港口暂停了两个夜间装卸窗口");
  await form.getByLabel("审核状态").selectOption("revised");
  await form.getByLabel("最终标签").fill("供应链 / 物流 / E2E");
  await form.getByLabel("审核人").fill("e2e-article");
  await form.getByLabel("审核备注").fill("文章端到端测试");
  await waitForSaved(page);

  await page.reload();
  await selectProject(page, "demo_articles", "东部港口调整夜间作业安排");
  await expect(form.getByLabel("审核状态")).toHaveValue("revised");
  await expect(form.getByLabel("最终标签")).toHaveValue("供应链 / 物流 / E2E");
  await expect(form.getByLabel("证据摘录")).toHaveValue(
    "东部港口暂停了两个夜间装卸窗口",
  );
  await expect(form.getByLabel("审核人")).toHaveValue("e2e-article");
  await expect(form.getByLabel("审核备注")).toHaveValue("文章端到端测试");

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "导出 JSONL" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^demo_articles-.*\.jsonl$/);
  const rows = parseExport(await downloadText(download));
  const article = rows.find((row) => row.item_id === "article_001");
  expect(article).toMatchObject({
    item_id: "article_001",
    revision: 1,
    status: "revised",
    note: "文章端到端测试",
    values: {
      reviewer: "e2e-article",
      evidence_quote: "东部港口暂停了两个夜间装卸窗口",
      final_tags: ["供应链", "物流", "E2E"],
    },
  });
});

test("graph edits persist atomically and export the final structure", async ({ page }) => {
  await page.goto("/");
  await selectProject(page, "demo_graphs", "东部港口夜间装卸受限");

  const nodeOne = page.locator('[data-node-id="n1"]');
  await nodeOne
    .getByLabel("节点名称")
    .fill("岸桥控制系统异常（已复核）");
  await nodeOne.getByRole("button", { name: "应用修改" }).click();

  await page.getByRole("button", { name: "+ 新增节点" }).click();
  const addNode = page.getByTestId("add-node-form");
  await addNode.getByLabel("节点类型").selectOption("control");
  await addNode.getByLabel("节点名称").fill("转移高时效货物");
  await addNode.getByLabel("证据原文").fill("把高时效货物转移到南区泊位");
  await addNode.getByRole("button", { name: "添加", exact: true }).click();

  await page.getByRole("button", { name: "+ 新增关系" }).click();
  const addEdge = page.getByTestId("add-edge-form");
  await addEdge.getByLabel("起点").selectOption("n4");
  await addEdge.getByLabel("关系").selectOption("mitigates");
  await addEdge.getByLabel("终点").selectOption("n2");
  await addEdge.getByLabel("证据原文").fill("把高时效货物转移到南区泊位");
  await addEdge.getByRole("button", { name: "添加", exact: true }).click();

  page.once("dialog", (dialog) => dialog.accept());
  await page
    .locator('[data-node-id="n3"]')
    .getByRole("button", { name: "删除", exact: true })
    .click();

  const form = page.getByTestId("graph-review-form");
  await form.getByLabel("审核状态").selectOption("revised");
  await form.getByLabel("审核人").fill("e2e-graph");
  await form.getByLabel("审核备注").fill("图结构端到端测试");
  await waitForSaved(page);

  await page.reload();
  await selectProject(page, "demo_graphs", "东部港口夜间装卸受限");
  await expect(
    page.locator('[data-node-id="n1"]').getByLabel("节点名称"),
  ).toHaveValue("岸桥控制系统异常（已复核）");
  await expect(page.locator('[data-node-id="n4"]')).toHaveCount(1);
  await expect(page.locator('[data-node-id="n3"]')).toHaveCount(0);
  await expect(page.locator('[data-edge-id="e3"]')).toHaveCount(1);
  await expect(page.locator('[data-edge-id="e2"]')).toHaveCount(0);
  await expect(form.getByLabel("审核状态")).toHaveValue("revised");
  await expect(form.getByLabel("审核人")).toHaveValue("e2e-graph");
  await expect(form.getByLabel("审核备注")).toHaveValue("图结构端到端测试");

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "导出 JSONL" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^demo_graphs-.*\.jsonl$/);
  const rows = parseExport(await downloadText(download));
  const graph = rows.find((row) => row.item_id === "graph_001");
  expect(graph).toBeDefined();
  expect(graph?.status).toBe("revised");
  expect(graph?.revision).toBe(1);
  expect(graph?.note).toBe("图结构端到端测试");

  const nodes = graph?.values.final_nodes as Array<Record<string, string>>;
  const edges = graph?.values.final_edges as Array<Record<string, string>>;
  expect(nodes).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ id: "n1", label: "岸桥控制系统异常（已复核）" }),
      expect.objectContaining({ id: "n4", label: "转移高时效货物" }),
    ]),
  );
  expect(nodes.map((node) => node.id)).not.toContain("n3");
  expect(edges).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        id: "e3",
        source: "n4",
        target: "n2",
        type: "mitigates",
      }),
    ]),
  );
  expect(edges.map((edge) => edge.id)).not.toContain("e2");
});
