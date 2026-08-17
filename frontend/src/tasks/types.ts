import type { ComponentType } from "react";

import type {
  ProjectTask,
  ReviewItem,
  ReviewPatch,
  SaveState,
} from "../types";

export type TaskViewProps = {
  item: ReviewItem;
  draft: unknown;
  task: ProjectTask;
  datasetVersion: string;
  saveState: SaveState;
  canMovePrevious: boolean;
  canMoveNext: boolean;
  onDraftChange: (draft: unknown) => void;
  onMove: (offset: number) => void;
};

export type TaskPlugin = {
  key: string;
  createDraft: (item: ReviewItem) => unknown;
  toReviewPatch: (draft: unknown) => ReviewPatch;
  onSaved?: (draft: unknown) => void;
  View: ComponentType<TaskViewProps>;
};
