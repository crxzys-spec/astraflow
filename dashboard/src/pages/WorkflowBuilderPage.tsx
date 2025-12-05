import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { nanoid } from "nanoid";
import { toPng } from "html-to-image";
import type { FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ReactFlowProvider } from "reactflow";
import {
  getGetPackageQueryOptions,
  useGetPackage,
  useGetWorkflow,
  useListPackages,
  useListRuns,
  useListWorkflowPackages,
  usePersistWorkflow,
  usePublishWorkflow,
  useStartRun,
  useCancelRun
} from "../api/endpoints";
import type { StartRunMutationError } from "../api/endpoints";
import type { AxiosError } from "axios";
import { WidgetRegistryProvider, useWorkflowStore } from "../features/workflow";
import type { WorkflowNodeStateUpdateMap } from "../features/workflow";
import { workflowDraftToDefinition } from "../features/workflow/utils/converters";
import type {
  WorkflowDefinition,
  WorkflowDraft,
  WorkflowGraphScope,
  WorkflowPaletteNode,
  WorkflowSubgraphDraftEntry,
  XYPosition
} from "../features/workflow";
import WorkflowCanvas from "../features/workflow/components/WorkflowCanvas";
import WorkflowPalette, { type PaletteNode } from "../features/workflow/components/WorkflowPalette";
import NodeInspector from "../features/workflow/components/NodeInspector";
import RunDetailPage from "./RunDetailPage";
import StatusBadge from "../components/StatusBadge";
import { getClientSessionId } from "../lib/clientSession";
import { client } from "../lib/httpClient";
import { UiEventType } from "../api/models/uiEventType";
import type { UiEventEnvelope } from "../api/models/uiEventEnvelope";
import type { RunStatusEvent } from "../api/models/runStatusEvent";
import type { RunSnapshotEvent } from "../api/models/runSnapshotEvent";
import type { NodeStateEvent } from "../api/models/nodeStateEvent";
import type { NodeResultSnapshotEvent } from "../api/models/nodeResultSnapshotEvent";
import type { RunStatus } from "../api/models/runStatus";
import { sseClient } from "../lib/sseClient";
import {
  upsertRunCaches,
  applyRunDefinitionSnapshot,
  replaceRunSnapshot,
  updateRunCaches,
  updateRunDefinitionNodeRuntime,
  updateRunDefinitionNodeState,
} from "../lib/sseCache";
import { useAuthStore } from "../features/auth/store";
import { useToolbarStore } from "../features/workflow/hooks/useToolbar";

const isEditableTarget = (target: EventTarget | null): boolean => {
  const element = target as HTMLElement | null;
  if (!element) {
    return false;
  }
  const tag = element.tagName?.toLowerCase();
  if (["input", "textarea", "select", "option"].includes(tag)) {
    return true;
  }
  if (element.isContentEditable) {
    return true;
  }
  return false;
};

const IconSave = () => (
  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 3h8l3 3v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
    <path d="M5 3v5h8V3" />
    <path d="M7.5 12.5h5" />
  </svg>
);

const IconPublish = () => (
  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 4v9" />
    <path d="M6.5 7.5 10 4l3.5 3.5" />
    <path d="M4 15.5h12" />
  </svg>
);

const IconRun = () => (
  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 4.5v11l8-5.5-8-5.5z" />
  </svg>
);

const IconInspector = () => (
  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3.5" y="6" width="13" height="8" rx="2" />
    <path d="M6.5 3.5v3" />
    <path d="M13.5 3.5v3" />
    <path d="M6.5 14v3" />
    <path d="M13.5 14v3" />
  </svg>
);

const IconRunsTab = () => (
  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4.5 15.5h11" />
    <path d="M5.5 12V8.5h3V12" />
    <path d="M9.5 12V6.5h3V12" />
    <path d="M13.5 12V5h3V12" />
  </svg>
);

const IconCatalog = () => (
  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3.5" y="3.5" width="6" height="6" rx="1.2" />
    <rect x="10.5" y="3.5" width="6" height="6" rx="1.2" />
    <rect x="3.5" y="10.5" width="6" height="6" rx="1.2" />
    <rect x="10.5" y="10.5" width="6" height="6" rx="1.2" />
  </svg>
);

const IconViews = () => (
  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 6.5h12" />
    <path d="M4 10h12" />
    <path d="M4 13.5h12" />
    <path d="M6.5 4v12" />
    <path d="M13.5 4v12" />
  </svg>
);

const DEFAULT_PALETTE_WIDTH = 340;
const DEFAULT_INSPECTOR_WIDTH = 360;

interface GraphSwitcherProps {
  activeGraph: WorkflowGraphScope;
  subgraphs: WorkflowSubgraphDraftEntry[];
  workflowName?: string;
  workflowId?: string;
  onSelect: (scope: WorkflowGraphScope) => void;
  onInline?: (subgraphId: string) => void;
  inlineMessage?: { subgraphId: string; type: "success" | "error"; text: string } | null;
}

const GraphSwitcher = ({
  activeGraph,
  subgraphs,
  workflowName,
  workflowId,
  onSelect,
  onInline,
  inlineMessage,
}: GraphSwitcherProps) => {
  const mainActive = activeGraph.type === "root";
  return (
    <div className="graph-switcher">
      <div className="graph-switcher__section">
        <div
          role="button"
          tabIndex={0}
          className={`graph-switcher__option ${mainActive ? "is-active" : ""}`}
          aria-pressed={mainActive}
          onClick={() => onSelect({ type: "root" })}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              onSelect({ type: "root" });
            }
          }}
        >
          <div className="graph-switcher__option-primary">
            <span className="graph-switcher__eyebrow">Primary workflow</span>
            <strong>{workflowName ?? "Untitled workflow"}</strong>
            <p className="graph-switcher__helper">Drag nodes from the catalog to build the main flow.</p>
          </div>
          <div className="graph-switcher__meta">
            <code>{workflowId}</code>
          </div>
        </div>
      </div>
      <div className="graph-switcher__section">
        <div className="graph-switcher__section-heading">
          <h4>Subgraphs</h4>
          <span className="graph-switcher__count">{subgraphs.length}</span>
        </div>
        {subgraphs.length ? (
          <div className="graph-switcher__list">
            {subgraphs.map((entry) => {
              const isActive = activeGraph.type === "subgraph" && activeGraph.subgraphId === entry.id;
              const label = entry.definition.metadata?.name ?? entry.definition.id;
              const description = entry.metadata?.description ?? entry.definition.metadata?.description;
              const nodeCount = Object.keys(entry.definition.nodes).length;
              return (
                <div
                  key={entry.id}
                  role="button"
                  tabIndex={0}
                  className={`graph-switcher__option ${isActive ? "is-active" : ""}`}
                  aria-pressed={isActive}
                  onClick={() => onSelect({ type: "subgraph", subgraphId: entry.id })}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect({ type: "subgraph", subgraphId: entry.id });
                    }
                  }}
                >
                  <div className="graph-switcher__option-primary">
                    <span className="graph-switcher__eyebrow">Container target</span>
                    <strong>{label}</strong>
                    {description && <p>{description}</p>}
                    {typeof onInline === "function" && (
                      <div className="graph-switcher__actions">
                        <button
                          type="button"
                          className="btn btn--ghost"
                          onClick={(event) => {
                            event.stopPropagation();
                            onInline(entry.id);
                          }}
                          title="Inline this subgraph into the current graph."
                        >
                          Dissolve subgraph
                        </button>
                        {inlineMessage && inlineMessage.subgraphId === entry.id && (
                          <small
                            className={
                              inlineMessage.type === "error" ? "error" : "text-subtle"
                            }
                          >
                            {inlineMessage.text}
                          </small>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="graph-switcher__meta">
                    <code>{entry.id}</code>
                    <span>{nodeCount} nodes</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="graph-switcher__empty">
            No localized subgraphs yet. Container nodes referencing reusable workflows will be managed here.
          </p>
        )}
      </div>
    </div>
  );
};

interface RunsInspectorPanelProps {
  onSelectRun: (runId: string) => void;
}

const RunsInspectorPanel = ({ onSelectRun }: RunsInspectorPanelProps) => {
  const canViewRuns = useAuthStore((state) =>
    state.hasRole(["admin", "run.viewer", "workflow.editor"])
  );
  const queryClient = useQueryClient();
  const cancelRun = useCancelRun(
    {
      mutation: {
        onSuccess: (_result, variables) => {
          const runId = variables?.runId;
          if (runId) {
            updateRunCaches(queryClient, runId, (run) =>
              run.runId === runId ? { ...run, status: "cancelled" } : run
            );
          }
        }
      }
    },
    queryClient
  );
  const { data, isLoading, isError, error, refetch } = useListRuns(undefined, {
    query: { enabled: canViewRuns }
  });
  const runs = data?.data.items ?? [];

  useEffect(() => {
    if (!canViewRuns) {
      return;
    }
    const unsubscribe = sseClient.subscribe((event) => {
      if (event.type === UiEventType.runstatus && event.data?.kind === "run.status") {
        const payload = event.data as RunStatusEvent;
        const runId = payload.runId;
        updateRunCaches(queryClient, runId, (run) => {
          if (run.runId !== runId) {
            return run;
          }
          const next = { ...run, status: payload.status };
          if (payload.startedAt !== undefined) {
            next.startedAt = payload.startedAt ?? null;
          }
          if (payload.finishedAt !== undefined) {
            next.finishedAt = payload.finishedAt ?? null;
          }
          return next;
        });
      } else if (
        event.type === UiEventType.runsnapshot &&
        event.data?.kind === "run.snapshot" &&
        event.data.run?.runId
      ) {
        const snapshot = event.data as RunSnapshotEvent;
        const runId = snapshot.run.runId;
        const combinedRun = {
          ...snapshot.run,
          nodes: snapshot.nodes ?? snapshot.run.nodes,
        };
        replaceRunSnapshot(queryClient, runId, combinedRun);
      }
    });
    return () => unsubscribe();
  }, [canViewRuns, queryClient]);

  if (!canViewRuns) {
    return (
      <div className="inspector-panel__empty">
        <p>You do not have permission to view runs.</p>
      </div>
    );
  }

  if (isLoading) {
    return <div className="inspector-panel__loading">Loading runs...</div>;
  }

  if (isError) {
    return (
      <div className="inspector-panel__empty">
        <p>Failed to load runs: {(error as Error).message}</p>
        <button className="btn btn--ghost" type="button" onClick={() => refetch()}>
          Retry
        </button>
      </div>
    );
  }

  if (!runs.length) {
    return (
      <div className="inspector-panel__empty">
        <p>No runs yet.</p>
        <button className="btn btn--ghost" type="button" onClick={() => refetch()}>
          Refresh
        </button>
      </div>
    );
  }

  return (
    <div className="runs-panel">
      <div className="runs-panel__header">
        <div>
          <h4>Recent runs</h4>
          <p className="text-subtle">Latest execution attempts</p>
        </div>
        <button className="btn btn--ghost runs-panel__refresh" type="button" onClick={() => refetch()}>
          Refresh
        </button>
      </div>
      <div className="runs-panel__list">
        {runs.map((run) => {
          const isCancelable = run.status === "running" || run.status === "queued";
          const isCancelling = cancelRun.isPending && cancelRun.variables?.runId === run.runId;
          return (
            <div
              key={run.runId}
              className="runs-panel__item"
              role="button"
              tabIndex={0}
              onClick={() => onSelectRun(run.runId)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectRun(run.runId);
                }
              }}
            >
              <div className="runs-panel__identity">
                <p className="runs-panel__run-id">{run.runId}</p>
                <p className="runs-panel__meta">Client {run.clientId ?? "—"}</p>
              </div>
              <div className="runs-panel__status">
                <StatusBadge status={run.status} />
                <span>{run.startedAt ?? "Pending"}</span>
              </div>
              {isCancelable && (
                <button
                  type="button"
                  className="btn btn--ghost runs-panel__stop"
                  onClick={(event) => {
                    event.stopPropagation();
                    cancelRun.mutate(
                      { runId: run.runId },
                      { onError: (mutationError) => console.error("Failed to stop run", mutationError) }
                    );
                  }}
                  disabled={isCancelling}
                >
                  {isCancelling ? "Stopping..." : "Stop"}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const composeWorkflowDefinition = (
  draft: WorkflowDraft,
  subgraphs: WorkflowSubgraphDraftEntry[]
): WorkflowDefinition => {
  const persistableSubgraphs = subgraphs.map((entry) => ({
    id: entry.id,
    metadata: entry.metadata,
    definition: workflowDraftToDefinition(entry.definition),
  }));
  return workflowDraftToDefinition({
    ...draft,
    subgraphs: persistableSubgraphs.length ? persistableSubgraphs : undefined,
  });
};

const getErrorMessage = (error: unknown): string => {
  if (!error) {
    return "Unknown error.";
  }
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: { message?: string } } }).response;
    if (response?.data?.message) {
      return response.data.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error.";
};

const slugifyValue = (value: string): string =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);

const normalizeVisibility = (value?: string | null): PublishFormState["visibility"] => {
  if (value === "public" || value === "internal") {
    return value;
  }
  return "private";
};

const STALE_TIME_MS = 5 * 60_000;

const createEmptyWorkflow = (id: string, name: string): WorkflowDefinition => ({
  id,
  schemaVersion: "2025-10",
  metadata: {
    name,
    namespace: "default",
    originId: id,
  },
  nodes: [],
  edges: [],
});

const extractRunId = (event: UiEventEnvelope): string | undefined => {
  const scopeRunId = event.scope?.runId;
  const data = event.data as Record<string, unknown> | undefined;
  if (!data) {
    return scopeRunId;
  }
  if (typeof data.runId === "string") {
    return data.runId;
  }
  const run = data.run as { runId?: unknown } | undefined;
  if (run && typeof run.runId === "string") {
    return run.runId;
  }
  return scopeRunId;
};

type RunMessage =
  | { type: "success"; runId?: string; text: string }
  | { type: "error"; text: string };

type PublishMessage = { type: "success" | "error"; text: string };

type PublishFormState = {
  version: string;
  displayName: string;
  summary: string;
  visibility: "private" | "public" | "internal";
  changelog: string;
  mode: "new" | "existing";
  slug: string;
  packageId: string;
};

const VISIBILITY_OPTIONS: PublishFormState["visibility"][] = ["private", "internal", "public"];

const WorkflowBuilderPage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { workflowId } = useParams<{ workflowId: string }>();

  const loadWorkflow = useWorkflowStore((state) => state.loadWorkflow);
  const resetWorkflow = useWorkflowStore((state) => state.resetWorkflow);
  const setPreviewImage = useWorkflowStore((state) => state.setPreviewImage);
  const workflow = useWorkflowStore((state) => state.workflow);
  const subgraphDrafts = useWorkflowStore((state) => state.subgraphDrafts);
  const activeGraph = useWorkflowStore((state) => state.activeGraph);
  const setActiveGraph = useWorkflowStore((state) => state.setActiveGraph);
  const addNodeFromTemplate = useWorkflowStore((state) => state.addNodeFromTemplate);
  const selectedNodeId = useWorkflowStore((state) => state.selectedNodeId);
  const inlineSubgraph = useWorkflowStore((state) => state.inlineSubgraphIntoActiveGraph);
  const undo = useWorkflowStore((state) => state.undo);
  const redo = useWorkflowStore((state) => state.redo);
  const canUndo = useWorkflowStore((state) => state.canUndo);
  const canRedo = useWorkflowStore((state) => state.canRedo);
  const toWorkflowDefinition = useCallback(
    (draft: WorkflowDraft) => composeWorkflowDefinition(draft, subgraphDrafts),
    [subgraphDrafts]
  );
  const updateNodeStates = useWorkflowStore((state) => state.updateNodeStates);
  const hasHydrated = useRef(false);
  const lastHydrateAt = useRef<number>(0);

  const canEditWorkflow = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));

  const [selectedPackageName, setSelectedPackageName] = useState<string>();
  const [selectedVersion, setSelectedVersion] = useState<string>();
  const [runMessage, setRunMessage] = useState<RunMessage | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | undefined>();
  const activeRunRef = useRef<string | undefined>();
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const [publishMessage, setPublishMessage] = useState<PublishMessage | null>(null);
  const [isPublishModalOpen, setPublishModalOpen] = useState(false);
  const [publishForm, setPublishForm] = useState<PublishFormState>({
    version: "",
    displayName: "",
    summary: "",
    visibility: "private",
    changelog: "",
    mode: "new",
    slug: "",
    packageId: ""
  });
  const [slugEdited, setSlugEdited] = useState(false);
  const [publishModalError, setPublishModalError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<PublishMessage | null>(null);
  const [isPaletteOpen, setPaletteOpen] = useState(true);
  const [isInspectorOpen, setInspectorOpen] = useState(true);
  const [activePaletteTab, setActivePaletteTab] = useState<"catalog" | "graphs">("catalog");
  const [activeInspectorTab, setActiveInspectorTab] = useState<"inspector" | "runs">("inspector");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [activeRunStatus, setActiveRunStatus] = useState<RunStatus | undefined>();
  const [inlineMessage, setInlineMessage] = useState<{ subgraphId: string; type: "success" | "error"; text: string } | null>(null);
  const toolbarRef = useRef<React.ReactNode | null>(null);

  const handleInlineFromSwitcher = useCallback(
    (subgraphId: string) => {
      const runInline = () => {
        const result = inlineSubgraph(undefined, subgraphId);
        setInlineMessage({
          subgraphId,
          type: result.ok ? "success" : "error",
          text: result.ok ? "Inlined into the current graph." : result.error ?? "Unable to inline.",
        });
      };
      if (activeGraph.type === "subgraph") {
        setActiveGraph({ type: "root" }, { recordHistory: false });
        // Defer to next tick so UI有机会切回主视图后再执行。
        setTimeout(runInline, 0);
        return;
      }
      runInline();
    },
    [activeGraph.type, inlineSubgraph, setActiveGraph]
  );

  useEffect(() => {
    const handleKeydown = (event: KeyboardEvent) => {
      const isMac = typeof navigator !== "undefined" && /mac/i.test(navigator.platform);
      const isMetaPressed = isMac ? event.metaKey : event.ctrlKey;
      if (!isMetaPressed || isEditableTarget(event.target)) {
        return;
      }
      const key = event.key.toLowerCase();
      if (key === "z" && !event.shiftKey) {
        if (canUndo()) {
          event.preventDefault();
          undo();
        }
      } else if (key === "y" || (key === "z" && event.shiftKey)) {
        if (canRedo()) {
          event.preventDefault();
          redo();
        }
      }
    };
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, [canRedo, canUndo, redo, undo]);

  const readStoredPanelWidth = (key: "paletteWidth" | "inspectorWidth", fallback: number) => {
    if (typeof window === "undefined") {
      return fallback;
    }
    const stored = localStorage.getItem(`builder.${key}`);
    if (!stored) {
      return fallback;
    }
    const parsed = Number.parseInt(stored, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  };

  const [paletteWidth, setPaletteWidth] = useState<number>(() =>
    readStoredPanelWidth("paletteWidth", DEFAULT_PALETTE_WIDTH)
  );
  const [inspectorWidth, setInspectorWidth] = useState<number>(() =>
    readStoredPanelWidth("inspectorWidth", DEFAULT_INSPECTOR_WIDTH)
  );
  const handlePaletteTabSelect = useCallback(
    (tab: "catalog" | "graphs") => {
      if (activePaletteTab === tab) {
        setPaletteOpen((open) => !open);
        return;
      }
      setActivePaletteTab(tab);
      setPaletteOpen(true);
    },
    [activePaletteTab]
  );

  const handleInspectorTabSelect = useCallback(
    (tab: "inspector" | "runs") => {
      if (activeInspectorTab === tab) {
        setInspectorOpen((open) => !open);
        return;
      }
      setActiveInspectorTab(tab);
      setInspectorOpen(true);
    },
    [activeInspectorTab]
  );

  const resizeStateRef = useRef<{
    type: "palette" | "inspector";
    startX: number;
    startWidth: number;
  } | null>(null);

  const handleResizeStart = useCallback(
    (type: "palette" | "inspector") => (event: React.MouseEvent) => {
      event.preventDefault();
      event.stopPropagation();
      const startX = event.clientX;
      const startWidth = type === "palette" ? paletteWidth : inspectorWidth;
      resizeStateRef.current = { type, startX, startWidth };
      document.body.classList.add("is-resizing");
    },
    [paletteWidth, inspectorWidth]
  );

  useEffect(() => {
    const handleMove = (event: MouseEvent) => {
      const state = resizeStateRef.current;
      if (!state) {
        return;
      }
      const delta = event.clientX - state.startX;
      if (state.type === "palette") {
        const nextWidth = Math.min(800, Math.max(220, state.startWidth + delta));
        setPaletteWidth(nextWidth);
        localStorage.setItem("builder.paletteWidth", String(nextWidth));
      } else {
        const nextWidth = Math.min(820, Math.max(260, state.startWidth - delta));
        setInspectorWidth(nextWidth);
        localStorage.setItem("builder.inspectorWidth", String(nextWidth));
      }
    };
    const handleUp = () => {
      if (resizeStateRef.current) {
        resizeStateRef.current = null;
        document.body.classList.remove("is-resizing");
      }
    };
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
    };
  }, []);

  const isNewSession = !workflowId || workflowId === "new";
  const workflowKey = !isNewSession ? workflowId : undefined;

  const workflowQuery = useGetWorkflow(workflowKey ?? "", {
    query: { enabled: Boolean(workflowKey) }
  });

  const packagesQuery = useListPackages({
    query: { staleTime: STALE_TIME_MS }
  });
  const workflowPackagesQuery = useListWorkflowPackages(
    canEditWorkflow ? { owner: "me", limit: 200 } : undefined,
    {
      query: { enabled: canEditWorkflow, staleTime: STALE_TIME_MS }
    }
  );

  const startRun = useStartRun(undefined, queryClient);
  const cancelRun = useCancelRun(undefined, queryClient);
  const setToolbar = useToolbarStore((state) => state.setContent);
  const publishWorkflowMutation = usePublishWorkflow(undefined, queryClient);
  const persistWorkflowMutation = usePersistWorkflow(undefined, queryClient);

  const captureCanvasPreview = useCallback(async () => {
    if (typeof window === "undefined") {
      return undefined;
    }
    const node = canvasRef.current;
    if (!node) {
      return undefined;
    }
    try {
      return await toPng(node, {
        cacheBust: true,
        pixelRatio: Math.min(window.devicePixelRatio || 1, 2),
        backgroundColor: "#020617",
      });
    } catch (error) {
      console.warn("Failed to capture workflow preview.", error);
      return undefined;
    }
  }, []);

  const sendWorkflowPreview = useCallback(async (workflowId: string, preview?: string | null) => {
    if (!preview) return;
    try {
      await client({
        method: "PUT",
        url: `/api/v1/workflows/${workflowId}/preview`,
        data: { previewImage: preview }
      });
    } catch (error) {
      console.warn("Failed to upload workflow preview", error);
    }
  }, []);

  const packageSummaries = packagesQuery.data?.data?.items ?? [];
  const ownedWorkflowPackages = workflowPackagesQuery.data?.data?.items ?? [];
  const canTargetExistingPackage = ownedWorkflowPackages.length > 0;
  const workflowPackagesErrorMessage = workflowPackagesQuery.isError
    ? getErrorMessage(workflowPackagesQuery.error)
    : null;
  const canPublishWorkflow = canEditWorkflow && Boolean(workflowKey);

  const openPublishModal = () => {
    if (!canPublishWorkflow || !workflow) {
      return;
    }
    const preferredName = workflow.metadata?.name ?? workflow.id ?? "";
    const preferredSummary = workflow.metadata?.description ?? "";
    const suggestedSlug = slugifyValue(preferredName || workflow.id || "");
    const matchedPackage =
      ownedWorkflowPackages.find((pkg) => pkg.slug === suggestedSlug) ?? null;
    const defaultMode: PublishFormState["mode"] = matchedPackage ? "existing" : "new";
    const defaultVisibility = normalizeVisibility(matchedPackage?.visibility);
    setPublishForm({
      version: "",
      displayName: preferredName,
      summary: preferredSummary,
      visibility: defaultVisibility,
      changelog: "",
      mode: defaultMode,
      slug: suggestedSlug,
      packageId: matchedPackage?.id ?? ownedWorkflowPackages[0]?.id ?? ""
    });
    setSlugEdited(false);
    setPublishModalError(null);
    setPublishModalOpen(true);
  };

  const closePublishModal = () => {
    if (publishWorkflowMutation.isPending) {
      return;
    }
    setPublishModalOpen(false);
    setSlugEdited(false);
  };

  const handlePublishSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!workflow?.id) {
      setPublishModalError("Workflow is not loaded.");
      return;
    }
    const trimmedVersion = publishForm.version.trim();
    if (!trimmedVersion) {
      setPublishModalError("Version is required.");
      return;
    }
    if (publishForm.mode === "existing" && !publishForm.packageId) {
      setPublishModalError("Select a package to publish a new version.");
      return;
    }
    setPublishModalError(null);
    const displayName =
      publishForm.displayName.trim() ||
      workflow.metadata?.name ||
      workflow.id;
    const payload = {
      version: trimmedVersion,
      displayName,
      summary: publishForm.summary.trim() || undefined,
      visibility: publishForm.visibility,
      changelog: publishForm.changelog.trim() || undefined,
    } as {
      version: string;
      displayName: string;
      summary?: string;
      visibility: PublishFormState["visibility"];
      changelog?: string;
      packageId?: string;
      slug?: string;
    };
    if (publishForm.mode === "existing") {
      payload.packageId = publishForm.packageId;
    } else {
      const slugSource = publishForm.slug || displayName || workflow.id;
      const normalizedSlug = slugifyValue(slugSource);
      if (!normalizedSlug) {
        setPublishModalError("Slug is required when creating a new package.");
        return;
      }
      payload.slug = normalizedSlug;
    }

    const previewImage =
      (await captureCanvasPreview()) ?? workflow.previewImage ?? undefined;
    if (previewImage) {
      setPreviewImage(previewImage);
    }

    publishWorkflowMutation.mutate(
      {
        workflowId: workflow.id,
        data: payload
      },
      {
        onSuccess: async (response) => {
          const versionLabel = response.data?.version ?? publishForm.version.trim();
          setPublishMessage({
            type: "success",
            text: `Workflow published as version ${versionLabel}.`
          });
          await sendWorkflowPreview(workflow.id, previewImage);
          setPublishModalOpen(false);
        },
        onError: (error) => {
          setPublishModalError(getErrorMessage(error));
        }
      }
    );
  };

  useEffect(() => {
    if (!isPublishModalOpen) {
      return;
    }
    if (publishForm.mode !== "new") {
      return;
    }
    if (slugEdited) {
      return;
    }
    const fallback =
      publishForm.displayName || workflow?.metadata?.name || workflow?.id || "";
    const nextSlug = slugifyValue(fallback);
    if (nextSlug && nextSlug !== publishForm.slug) {
      setPublishForm((prev) => ({ ...prev, slug: nextSlug }));
    }
  }, [
    isPublishModalOpen,
    publishForm.mode,
    publishForm.displayName,
    publishForm.slug,
    slugEdited,
    workflow
  ]);

  useEffect(() => {
    if (!isPublishModalOpen) {
      return;
    }
    if (publishForm.mode !== "existing") {
      return;
    }
    if (publishForm.packageId) {
      return;
    }
    const firstPackage = ownedWorkflowPackages[0];
    if (firstPackage) {
      setPublishForm((prev) => ({
        ...prev,
        packageId: firstPackage.id,
        visibility: normalizeVisibility(firstPackage.visibility)
      }));
    }
  }, [
    isPublishModalOpen,
    publishForm.mode,
    publishForm.packageId,
    ownedWorkflowPackages
  ]);

  const handleSlugInputChange = (value: string) => {
    setSlugEdited(Boolean(value));
    setPublishForm((prev) => ({ ...prev, slug: slugifyValue(value) }));
  };

  const handlePackageSelectionChange = (packageId: string) => {
    const selected = ownedWorkflowPackages.find((pkg) => pkg.id === packageId);
    setPublishForm((prev) => ({
      ...prev,
      packageId,
      displayName: selected?.displayName ?? prev.displayName,
      summary: selected?.summary ?? prev.summary,
      visibility: normalizeVisibility(selected?.visibility),
    }));
  };

  const handlePublishModeChange = (mode: PublishFormState["mode"]) => {
    setPublishForm((prev) => {
      if (prev.mode === mode) {
        return prev;
      }
      if (mode === "existing") {
        const fallbackId = prev.packageId || ownedWorkflowPackages[0]?.id || "";
        const selected = ownedWorkflowPackages.find((pkg) => pkg.id === fallbackId);
        return {
          ...prev,
          mode,
          packageId: fallbackId,
          visibility: selected ? normalizeVisibility(selected.visibility) : prev.visibility,
        };
      }
      const fallbackName = prev.displayName || workflow?.metadata?.name || workflow?.id || "";
      return {
        ...prev,
        mode,
        packageId: "",
        slug: slugifyValue(fallbackName),
      };
    });
    if (mode === "new") {
      setSlugEdited(false);
    }
  };

  const handleSaveWorkflow = async () => {
    if (!workflow) {
      setSaveMessage({ type: "error", text: "Workflow is not loaded." });
      return;
    }
    const shouldAssignId =
      !workflowKey || workflowKey === "new" || workflow.id === "wf-local";
    const nextId = shouldAssignId
      ? (crypto.randomUUID ? crypto.randomUUID() : nanoid())
      : workflow.id;
    const workflowForPersist = {
      ...workflow,
      id: nextId,
      metadata: {
        ...(workflow.metadata ?? {}),
        originId: workflow.metadata?.originId ?? nextId,
      },
    };
    const previewImage =
      (await captureCanvasPreview()) ?? workflow.previewImage ?? undefined;
    if (previewImage) {
      setPreviewImage(previewImage);
    }
    const definition = toWorkflowDefinition(workflowForPersist);
    persistWorkflowMutation.mutate(
      { data: definition },
      {
        onSuccess: async (response) => {
          const workflowIdResponse = response.data?.workflowId ?? workflowForPersist.id;
          setSaveMessage({ type: "success", text: "Workflow saved successfully." });
          await sendWorkflowPreview(workflowIdResponse, previewImage);
          if (!workflowKey || workflowKey !== workflowIdResponse) {
            navigate(`/workflows/${workflowIdResponse}`, { replace: true });
          } else {
            workflowQuery.refetch();
          }
        },
        onError: (error) => {
          setSaveMessage({ type: "error", text: getErrorMessage(error) });
        }
      }
    );
  };

  const handleSelectPackage = useCallback(
    (packageName: string) => {
      setSelectedPackageName(packageName);
      const summary = packageSummaries.find((item) => item.name === packageName);
      const preferredVersion =
        summary?.defaultVersion ?? summary?.latestVersion ?? summary?.versions?.[0];
      setSelectedVersion(preferredVersion);
    },
    [packageSummaries]
  );

  const handleSelectVersion = useCallback((version: string) => {
    setSelectedVersion(version || undefined);
  }, []);

  useEffect(() => {
    resetWorkflow();
    hasHydrated.current = false;
  }, [workflowId, resetWorkflow]);

  useEffect(() => {
    if (!workflow) {
      hasHydrated.current = false;
    }
  }, [workflow]);

  useEffect(() => {
    if (isNewSession && !workflow) {
      const localId = workflowId && workflowId !== "new" ? workflowId : "wf-local";
      const localName =
        workflowId && workflowId !== "new" ? `Workflow ${workflowId}` : "Local Builder Session";
      loadWorkflow(createEmptyWorkflow(localId, localName));
    }
  }, [isNewSession, workflow, workflowId, loadWorkflow]);

  useEffect(() => {
    const definition = workflowQuery.data?.data;
    if (!definition) {
      return;
    }

    const updatedAt = workflowQuery.dataUpdatedAt ?? 0;
    if (hasHydrated.current && lastHydrateAt.current === updatedAt) {
      return;
    }
    lastHydrateAt.current = updatedAt;

    if (!hasHydrated.current || !workflow || workflow.id !== definition.id) {
      loadWorkflow(definition);
      hasHydrated.current = true;
      return;
    }

    // Avoid re-applying identical runtime states that would retrigger renders.
    const currentStateById = new Map<string, unknown>();
    if (workflow?.nodes) {
      Object.values(workflow.nodes).forEach((node) => currentStateById.set(node.id, node.state));
    }
    subgraphDrafts.forEach((entry) => {
      Object.values(entry.definition.nodes).forEach((node) => currentStateById.set(node.id, node.state));
    });

    const statesEqual = (left: unknown, right: unknown) =>
      JSON.stringify(left ?? null) === JSON.stringify(right ?? null);

    const updates: WorkflowNodeStateUpdateMap = {};
    (definition.nodes ?? []).forEach((node) => {
      if (node.state == null) {
        return;
      }
      const existing = currentStateById.get(node.id);
      if (!statesEqual(existing, node.state)) {
        updates[node.id] = node.state;
      }
    });

    if (Object.keys(updates).length > 0) {
      updateNodeStates(updates);
    }
  }, [workflowQuery.data, workflowQuery.dataUpdatedAt, workflow, subgraphDrafts, loadWorkflow, updateNodeStates]);

  const queryError = workflowQuery.error as AxiosError | undefined;
  const notFound =
    Boolean(workflowKey) &&
    workflowQuery.isError &&
    queryError?.response?.status === 404;
  const loadError =
    Boolean(workflowKey) &&
    workflowQuery.isError &&
    queryError?.response?.status !== 404 &&
    workflowQuery.error != null;

  useEffect(() => {
    if (notFound) {
      resetWorkflow();
    }
  }, [notFound, resetWorkflow]);

  useEffect(() => {
    if (!packageSummaries.length) {
      setSelectedPackageName(undefined);
      setSelectedVersion(undefined);
      return;
    }
    const currentSummary = selectedPackageName
      ? packageSummaries.find((item) => item.name === selectedPackageName)
      : undefined;
    if (!currentSummary) {
      const first = packageSummaries[0];
      setSelectedPackageName(first.name);
      const preferredVersion =
        first.defaultVersion ?? first.latestVersion ?? first.versions?.[0];
      setSelectedVersion(preferredVersion);
      return;
    }
    if (!currentSummary.versions.includes(selectedVersion ?? "")) {
      const preferredVersion =
        currentSummary.defaultVersion ??
        currentSummary.latestVersion ??
        currentSummary.versions?.[0];
      setSelectedVersion(preferredVersion);
    }
  }, [packageSummaries, selectedPackageName, selectedVersion]);

  const packageDetailQuery = useGetPackage(
    selectedPackageName ?? "",
    selectedPackageName
      ? selectedVersion
        ? { version: selectedVersion }
        : undefined
      : undefined,
    {
      query: { enabled: Boolean(selectedPackageName), staleTime: STALE_TIME_MS }
    }
  );

  const manifestNodes = packageDetailQuery.data?.data?.manifest?.nodes ?? [];

  const paletteItems = useMemo<PaletteNode[]>(
    () =>
      manifestNodes.map((node) => ({
        type: node.type ?? "",
        label: node.label ?? node.type ?? "",
        category: node.category ?? "uncategorised",
        role: node.role,
        description: node.description,
        tags: node.tags,
        status: node.status
      })),
    [manifestNodes]
  );

  const handleNodeDrop = useCallback(
    async (
      payload: { type: string; packageName?: string; packageVersion?: string },
      position: XYPosition
    ) => {
      try {
        const packageName = payload.packageName ?? selectedPackageName;
        if (!packageName) {
          throw new Error("Missing package selection for dropped node");
        }
        const response = await queryClient.ensureQueryData(
          getGetPackageQueryOptions(
            packageName,
            payload.packageVersion ? { version: payload.packageVersion } : undefined,
            { query: { staleTime: STALE_TIME_MS } }
          )
        );
        const definition = response?.data;
        if (!definition?.manifest?.nodes?.length) {
          throw new Error(`Package definition for "${packageName}" is missing nodes`);
        }
        const template = definition.manifest.nodes.find((node) => node.type === payload.type);
        if (!template) {
          throw new Error(`Node definition for "${payload.type}" is missing`);
        }
        const paletteNode: WorkflowPaletteNode = {
          template,
          packageName: definition.name,
          packageVersion: definition.version
        };
        addNodeFromTemplate(paletteNode, position);
      } catch (error) {
        console.error(`Failed to create node for type ${payload.type}`, error);
      }
    },
    [addNodeFromTemplate, queryClient, selectedPackageName]
  );

  const handleRunWorkflow = useCallback(() => {
    if (!workflow) {
      return;
    }
    if (!canEditWorkflow) {
      setRunMessage({
        type: "error",
        text: "You do not have permission to run workflows. Request workflow.editor access.",
      });
      return;
    }
    const definition = toWorkflowDefinition(workflow);
    setRunMessage(null);

    const clientSessionId = getClientSessionId();
    startRun.mutate(
      { data: { clientId: clientSessionId, workflow: definition } },
      {
        onSuccess: (result) => {
          const run = result.data;
          const runId = run?.runId;
          if (runId) {
            upsertRunCaches(queryClient, {
              runId,
              status: run.status as RunStatus,
              definitionHash: run.definitionHash ?? "",
              clientId: run.clientId ?? "",
              startedAt: null,
              finishedAt: null
            });
            const storeSnapshot = useWorkflowStore.getState();
            storeSnapshot.resetRunState();
            activeRunRef.current = runId;
            setActiveRunId(runId);
            setActiveRunStatus((run?.status as RunStatus) ?? "queued");
          }
          setRunMessage({
            type: "success",
            runId,
            text: runId ? `Run ${runId} queued` : "Run queued successfully",
          });
        },
        onError: (error: StartRunMutationError) => {
          const message =
            error.response?.data?.message ?? error.message ?? "Failed to start run";
          setRunMessage({ type: "error", text: message });
        },
      }
    );
  }, [startRun, workflow, canEditWorkflow, toWorkflowDefinition]);

  const handleCancelActiveRun = useCallback(() => {
    if (!activeRunId) {
      return;
    }
    cancelRun.mutate(
      { runId: activeRunId },
      {
        onSuccess: () => {
          setRunMessage({
            type: "success",
            runId: activeRunId,
            text: `Run ${activeRunId} cancellation requested`,
          });
          setActiveRunStatus("cancelled");
        },
        onError: (error) => {
          const message = getErrorMessage(error);
          setRunMessage({ type: "error", text: message });
        }
      }
    );
  }, [activeRunId, cancelRun, getErrorMessage, setRunMessage]);

  useEffect(() => {
    activeRunRef.current = activeRunId;
    if (!activeRunId) {
      setActiveRunStatus(undefined);
    }
  }, [activeRunId]);

  useEffect(() => {
    const unsubscribe = sseClient.subscribe((event) => {
      if (!event?.data || !event.type) {
        return;
      }
      let currentRunId = activeRunRef.current;
      const eventRunId = extractRunId(event);
      if (!currentRunId) {
        if (eventRunId && event.replayed !== true) {
          activeRunRef.current = eventRunId;
          currentRunId = eventRunId;
          setActiveRunId(eventRunId);
        } else {
          return;
        }
      }
      if (eventRunId && eventRunId !== currentRunId) {
        return;
      }
      if (event.scope?.runId && event.scope.runId !== currentRunId) {
        return;
      }
      if (event.type === UiEventType.runstatus && event.data?.kind === "run.status") {
        const payload = event.data as RunStatusEvent;
        if (payload.runId !== currentRunId) {
          return;
        }
        const status = payload.status;
        const readableStatus = status.replace(/[_-]+/g, " ").replace(/^\w/, (char) => char.toUpperCase());
        const messageSuffix = payload.reason ? ` (${payload.reason})` : "";
        const messageText = `Run ${payload.runId} ${readableStatus}${messageSuffix}`;
        setActiveRunStatus(status as RunStatus);
        setRunMessage({
          type: status === "failed" || status === "cancelled" ? "error" : "success",
          runId: payload.runId,
          text: messageText,
        });
        return;
      }
      if (event.type === UiEventType.runsnapshot && event.data?.kind === "run.snapshot") {
        const payload = event.data as RunSnapshotEvent;
        const snapshotRunId = payload.run?.runId;
        if (!snapshotRunId || snapshotRunId !== currentRunId) {
          return;
        }
        applyRunDefinitionSnapshot(queryClient, snapshotRunId, payload.nodes ?? undefined);
        return;
      }
      if (event.type === UiEventType.nodestate && event.data?.kind === "node.state") {
        const payload = event.data as NodeStateEvent;
        if (payload.runId !== currentRunId) {
          return;
        }
        updateRunDefinitionNodeState(
          queryClient,
          payload.runId,
          payload.nodeId,
          payload.state ?? null,
        );
        return;
      }
      if (
        event.type === UiEventType.noderesultsnapshot &&
        event.data?.kind === "node.result.snapshot"
      ) {
        const payload = event.data as NodeResultSnapshotEvent;
        if (payload.runId !== currentRunId) {
          return;
        }
        updateRunDefinitionNodeRuntime(queryClient, payload.runId, payload.nodeId, {
          result: payload.content ?? null,
          artifacts: payload.artifacts ?? null,
          summary: payload.summary ?? null,
        });
      }
    });
    return () => {
      unsubscribe();
    };
  }, [queryClient]);

  if (notFound) {
    return (
      <div className="card stack">
        <h2>Workflow not found</h2>
        <p className="text-subtle">
          The workflow "{workflowId}" does not exist. You can start a new session instead.
        </p>
        <div className="builder-actions">
          <button className="btn" type="button" onClick={() => navigate("/workflows/new")}>
            Start new builder session
          </button>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="card stack">
        <h2>Unable to load workflow</h2>
        <p className="error">
          {(queryError?.response?.data as { message?: string })?.message ??
            queryError?.message ??
            "An unexpected error occurred."}
        </p>
        <button className="btn" type="button" onClick={() => workflowKey && workflowQuery.refetch()}>
          Retry
        </button>
      </div>
    );
  }

  const packagesError = packagesQuery.isError ? (packagesQuery.error as Error) : undefined;
  const packageDetailError = packageDetailQuery.isError
    ? (packageDetailQuery.error as Error)
    : undefined;
  const derivedSlugForValidation =
    publishForm.mode === "new"
      ? slugifyValue(
          publishForm.slug ||
            publishForm.displayName ||
            workflow?.metadata?.name ||
            workflow?.id ||
            ""
        )
      : "";
  const isPublishValid =
    Boolean(publishForm.version.trim()) &&
    (publishForm.mode === "existing"
      ? Boolean(publishForm.packageId)
      : Boolean(derivedSlugForValidation));
  const publishInProgress = publishWorkflowMutation.isPending;

  const builderToolbar = useMemo(() => {
    if (!workflow) {
      return null;
    }
    return (
      <div className="builder-toolbar">
        <div className="builder-actions">
          {saveMessage && (
            <span
              className={`builder-alert builder-alert--${saveMessage.type}`}
              role={saveMessage.type === "error" ? "alert" : "status"}
            >
              {saveMessage.text}
            </span>
          )}
          {publishMessage && (
            <span
              className={`builder-alert builder-alert--${publishMessage.type}`}
              role={publishMessage.type === "error" ? "alert" : "status"}
            >
              {publishMessage.text}
            </span>
          )}
          {runMessage && (
            <span
              className={`builder-alert builder-alert--${runMessage.type}`}
              role={runMessage.type === "error" ? "alert" : "status"}
            >
              {runMessage.text}
            </span>
          )}
          {!canEditWorkflow && (
            <span className="builder-alert builder-alert--error">
              You have read-only access. Request workflow.editor rights to edit or run workflows.
            </span>
          )}
        </div>
        <div className="builder-actions builder-actions--buttons">
          {canEditWorkflow && (
            <button
              className="btn btn--ghost"
              type="button"
              onClick={handleSaveWorkflow}
              disabled={persistWorkflowMutation.isPending}
            >
              <span className="btn__icon" aria-hidden="true">
                <IconSave />
              </span>
              {persistWorkflowMutation.isPending ? "Saving..." : "Save"}
            </button>
          )}
          {canEditWorkflow && (
            <button
              className="btn btn--ghost"
              type="button"
              onClick={openPublishModal}
              disabled={!canPublishWorkflow}
              title={!canPublishWorkflow ? "Save before publishing." : undefined}
            >
              <span className="btn__icon" aria-hidden="true">
                <IconPublish />
              </span>
              Publish
            </button>
          )}
          <button
            className="btn btn--ghost"
            type="button"
            onClick={handleRunWorkflow}
            disabled={!canEditWorkflow || startRun.isPending}
          >
            <span className="btn__icon" aria-hidden="true">
              <IconRun />
            </span>
            {startRun.isPending ? "Launching..." : "Run"}
          </button>
          {activeRunId &&
            (!activeRunStatus || !["succeeded", "failed", "cancelled"].includes(activeRunStatus)) && (
              <button
                className="btn btn--ghost"
                type="button"
                onClick={handleCancelActiveRun}
                disabled={cancelRun.isPending && cancelRun.variables?.runId === activeRunId}
              >
                <span className="btn__icon" aria-hidden="true">
                  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
                    <rect x="5" y="5" width="10" height="10" rx="2" />
                  </svg>
                </span>
                {cancelRun.isPending && cancelRun.variables?.runId === activeRunId ? "Stopping..." : "Stop"}
              </button>
            )}
        </div>
      </div>
    );
  }, [
    activeRunId,
    activeRunStatus,
    canEditWorkflow,
    handleRunWorkflow,
    handleSaveWorkflow,
    handleCancelActiveRun,
    openPublishModal,
    persistWorkflowMutation.isPending,
    runMessage,
    saveMessage,
    publishMessage,
    canPublishWorkflow,
    startRun.isPending,
    workflow,
    cancelRun.isPending,
    cancelRun.variables
  ]);

  useEffect(() => {
    if (builderToolbar !== toolbarRef.current) {
      setToolbar(builderToolbar);
      toolbarRef.current = builderToolbar;
    }
  }, [builderToolbar, setToolbar]);

  useEffect(
    () => () => {
      setToolbar(null);
      toolbarRef.current = null;
    },
    [setToolbar]
  );

  if (!workflow) {
    return <div className="card">Initializing builder...</div>;
  }

  const paletteFlyoutStyle = { width: `${paletteWidth}px` };
  const inspectorFlyoutStyle = { width: `${inspectorWidth}px` };
  const paletteHandleStyle = { left: `calc(1.5rem + ${paletteWidth}px - 0.4rem)` };
  const inspectorHandleStyle = { right: `calc(1.5rem + ${inspectorWidth}px - 0.4rem)` };
  const paletteSwitchStyle = {
    left: isPaletteOpen ? `calc(${paletteWidth}px + 3rem)` : "1.25rem"
  };
  const inspectorSwitchStyle = {
    right: isInspectorOpen ? `calc(${inspectorWidth}px + 3rem)` : "1.25rem"
  };

  return (
    <WidgetRegistryProvider>
      <section className="builder-screen">
        <div className="builder-stage">
          <div className="builder-stage__body">
            <ReactFlowProvider>
              <div className="builder-stage__canvas card card--canvas">
                <div className="builder-canvas__viewport" ref={canvasRef}>
                  <WorkflowCanvas onNodeDrop={canEditWorkflow ? handleNodeDrop : undefined} />
                </div>
              </div>
            </ReactFlowProvider>

            <div className="palette-switch" style={paletteSwitchStyle}>
              <div className="palette-tabs" role="group" aria-label="Workflow builder panels">
                <button
                  type="button"
                  className={`palette-tab ${
                    activePaletteTab === "catalog" && isPaletteOpen ? "is-active" : ""
                  }`}
                  aria-pressed={activePaletteTab === "catalog" && isPaletteOpen}
                  title="Catalog"
                  aria-label="Catalog"
                  data-label="Catalog"
                  onClick={() => handlePaletteTabSelect("catalog")}
                >
                  <span className="palette-tab__icon" aria-hidden="true">
                    <IconCatalog />
                  </span>
                </button>
                <button
                  type="button"
                  className={`palette-tab ${
                    activePaletteTab === "graphs" && isPaletteOpen ? "is-active" : ""
                  }`}
                  aria-pressed={activePaletteTab === "graphs" && isPaletteOpen}
                  title="Workflow views"
                  aria-label="Workflow views"
                  data-label="Workflow views"
                  onClick={() => handlePaletteTabSelect("graphs")}
                >
                  <span className="palette-tab__icon" aria-hidden="true">
                    <IconViews />
                  </span>
                </button>
              </div>
            </div>
            {isPaletteOpen && (
              <button
                type="button"
                className="builder-resize-handle builder-resize-handle--palette"
                onMouseDown={handleResizeStart("palette")}
                aria-label="Resize catalog panel"
                style={paletteHandleStyle}
              />
            )}

            <div
              className={`builder-flyout builder-flyout--palette card card--surface ${
                isPaletteOpen ? "is-open" : "is-collapsed"
              }`}
              style={paletteFlyoutStyle}
            >
              <div className="palette-tabpanel">
                {activePaletteTab === "catalog" ? (
                  canEditWorkflow ? (
                    <WorkflowPalette
                      packages={packageSummaries}
                      selectedPackageName={selectedPackageName}
                      selectedVersion={selectedVersion}
                      onSelectPackage={handleSelectPackage}
                      onSelectVersion={handleSelectVersion}
                      nodes={paletteItems}
                      isLoadingPackages={packagesQuery.isLoading}
                      isLoadingNodes={packageDetailQuery.isLoading}
                      packagesError={packagesError}
                      nodesError={packageDetailError}
                      onRetryPackages={() => packagesQuery.refetch()}
                      onRetryNodes={selectedPackageName ? () => packageDetailQuery.refetch() : undefined}
                    />
                  ) : (
                    <div className="palette__viewer-message">
                      Viewer role detected. Palette editing is disabled until you obtain workflow.editor access.
                    </div>
                  )
                ) : (
                  <GraphSwitcher
                    activeGraph={activeGraph}
                    subgraphs={subgraphDrafts}
                    workflowName={workflow.metadata?.name}
                    workflowId={workflow.id}
                    onSelect={setActiveGraph}
                    onInline={handleInlineFromSwitcher}
                    inlineMessage={inlineMessage}
                  />
                )}
              </div>
            </div>

            <div className="inspector-switch" style={inspectorSwitchStyle}>
              <div className="inspector-tabs-floating" role="group" aria-label="Inspector panels">
                <button
                  type="button"
                  className={`inspector-tab ${
                    isInspectorOpen && activeInspectorTab === "inspector" ? "is-active" : ""
                  }`}
                  aria-pressed={isInspectorOpen && activeInspectorTab === "inspector"}
                  title="Inspector"
                  aria-label="Inspector"
                  data-label="Inspector"
                  onClick={() => handleInspectorTabSelect("inspector")}
                  >
                  <span className="inspector-tab__icon" aria-hidden="true">
                    <IconInspector />
                  </span>
                </button>
                <button
                  type="button"
                  className={`inspector-tab ${
                    isInspectorOpen && activeInspectorTab === "runs" ? "is-active" : ""
                  }`}
                  aria-pressed={isInspectorOpen && activeInspectorTab === "runs"}
                  title="Runs"
                  aria-label="Runs"
                  data-label="Runs"
                  onClick={() => handleInspectorTabSelect("runs")}
                >
                  <span className="inspector-tab__icon" aria-hidden="true">
                    <IconRunsTab />
                  </span>
                </button>
              </div>
            </div>

            {isInspectorOpen && (
              <button
                type="button"
                className="builder-resize-handle builder-resize-handle--inspector"
                onMouseDown={handleResizeStart("inspector")}
                aria-label="Resize inspector panel"
                style={inspectorHandleStyle}
              />
            )}

            <div
              className={`builder-flyout builder-flyout--inspector card card--surface ${
                isInspectorOpen ? "is-open" : "is-collapsed"
              }`}
              style={inspectorFlyoutStyle}
            >
              <div className="inspector-panel">
                {activeInspectorTab === "inspector" ? (
                  <NodeInspector />
                ) : (
                  <RunsInspectorPanel onSelectRun={setSelectedRunId} />
                  )}
                </div>
              </div>
            </div>
          <div className="builder-stage__watermark">
            <span className="builder-watermark__title">{workflow.metadata?.name ?? "Untitled Workflow"}</span>
            <span className="builder-watermark__subtitle">ID: {workflow.id}</span>
          </div>
        </div>
      </section>
      {selectedRunId && (
        <RunDetailPage runIdOverride={selectedRunId} onClose={() => setSelectedRunId(null)} />
      )}
      {isPublishModalOpen && (
        <div className="modal">
          <div className="modal__backdrop" onClick={closePublishModal} />
          <form className="modal__panel card publish-modal" onSubmit={handlePublishSubmit}>
            <header className="modal__header">
              <div>
                <h3>Publish workflow</h3>
                <p className="text-subtle">Snapshot the current draft into the Store.</p>
              </div>
              <button className="modal__close" type="button" onClick={closePublishModal} aria-label="Close publish modal">
                ×
              </button>
            </header>
            <div className="publish-modal__grid">
              <div className="publish-modal__section publish-modal__field--full">
                <span className="publish-modal__label">Publish target</span>
                <div className="publish-modal__choices">
                  <label className="publish-modal__choice">
                    <input
                      type="radio"
                      name="publish-target"
                      value="new"
                      checked={publishForm.mode === "new"}
                      onChange={() => handlePublishModeChange("new")}
                    />
                    <div>
                      <strong>Create a new package</strong>
                      <p>Assign a fresh slug and visibility.</p>
                    </div>
                  </label>
                  <label
                    className={`publish-modal__choice${canTargetExistingPackage ? "" : " publish-modal__choice--disabled"}`}
                  >
                    <input
                      type="radio"
                      name="publish-target"
                      value="existing"
                      checked={publishForm.mode === "existing"}
                      onChange={() => handlePublishModeChange("existing")}
                      disabled={!canTargetExistingPackage}
                    />
                    <div>
                      <strong>Append to existing package</strong>
                      <p>Publish as a new semantic version.</p>
                    </div>
                  </label>
                  {!canTargetExistingPackage && (
                    <small className="publish-modal__helper">You have not published any packages yet.</small>
                  )}
                </div>
              </div>
              {publishForm.mode === "existing" ? (
                <label className="form-field publish-modal__field publish-modal__field--half">
                  <span>Package</span>
                  <select
                    value={publishForm.packageId}
                    onChange={(event) => handlePackageSelectionChange(event.target.value)}
                    disabled={workflowPackagesQuery.isLoading || !canTargetExistingPackage}
                  >
                    <option value="">Select a package</option>
                    {ownedWorkflowPackages.map((pkg) => (
                      <option key={pkg.id} value={pkg.id}>
                        {pkg.displayName} ({pkg.slug})
                      </option>
                    ))}
                  </select>
                  {workflowPackagesQuery.isLoading && (
                    <small className="publish-modal__helper">Loading your packages…</small>
                  )}
                  {workflowPackagesErrorMessage && (
                    <small className="error">Unable to load packages: {workflowPackagesErrorMessage}</small>
                  )}
                </label>
              ) : (
                <label className="form-field publish-modal__field publish-modal__field--half">
                  <span>Slug*</span>
                  <input
                    type="text"
                    value={publishForm.slug}
                    onChange={(event) => handleSlugInputChange(event.target.value)}
                    placeholder="friendly-workflow-name"
                  />
                  <small className="publish-modal__helper">
                    Used in Store URLs. Lowercase letters, numbers, and dashes only.
                  </small>
                </label>
              )}
              <label className="form-field publish-modal__field">
                <span>Version*</span>
                <input
                  type="text"
                  value={publishForm.version}
                  onChange={(event) => setPublishForm((prev) => ({ ...prev, version: event.target.value }))}
                  placeholder="e.g. 1.0.0"
                  required
                />
              </label>
              <label className="form-field publish-modal__field">
                <span>Display name</span>
                <input
                  type="text"
                  value={publishForm.displayName}
                  onChange={(event) =>
                    setPublishForm((prev) => ({ ...prev, displayName: event.target.value }))
                  }
                  placeholder="Workflow title"
                />
              </label>
              <label className="form-field publish-modal__field publish-modal__field--full">
                <span>Summary</span>
                <textarea
                  value={publishForm.summary}
                  onChange={(event) => setPublishForm((prev) => ({ ...prev, summary: event.target.value }))}
                  rows={3}
                />
              </label>
              <label className="form-field publish-modal__field">
                <span>Visibility</span>
                <select
                  value={publishForm.visibility}
                  onChange={(event) =>
                    setPublishForm((prev) => ({
                      ...prev,
                      visibility: event.target.value as PublishFormState["visibility"],
                    }))
                  }
                >
                  {VISIBILITY_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option.charAt(0).toUpperCase() + option.slice(1)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field publish-modal__field publish-modal__field--full">
                <span>Changelog</span>
                <textarea
                  value={publishForm.changelog}
                  onChange={(event) =>
                    setPublishForm((prev) => ({ ...prev, changelog: event.target.value }))
                  }
                  rows={3}
                />
              </label>
            </div>
            {publishModalError && (
              <div className="card card--error">
                <p className="error">{publishModalError}</p>
              </div>
            )}
            <footer className="modal__footer">
              <button className="btn" type="button" onClick={closePublishModal} disabled={publishInProgress}>
                Cancel
              </button>
              <button
                className="btn btn--primary"
                type="submit"
                disabled={!isPublishValid || publishInProgress}
              >
                {publishInProgress ? "Publishing..." : "Publish"}
              </button>
            </footer>
          </form>
        </div>
      )}
    </WidgetRegistryProvider>
  );
};

export default WorkflowBuilderPage;






