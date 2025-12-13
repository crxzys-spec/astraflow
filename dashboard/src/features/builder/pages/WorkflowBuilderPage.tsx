import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toPng } from "html-to-image";
import { useNavigate, useParams } from "react-router-dom";
import { ReactFlowProvider } from "reactflow";
import { useCatalogSearch } from "../../../hooks/useCatalogSearch";
import type { CatalogNode } from "../../../client/models";
import { WidgetRegistryProvider } from "..";
import { useWorkflowStore } from "../store";
import { workflowDraftToDefinition } from "../utils/converters";
import type { WorkflowDefinition, WorkflowDraft, WorkflowPaletteNode, WorkflowSubgraphDraftEntry, XYPosition } from "../types";
import WorkflowCanvas from "../components/WorkflowCanvas";
import WorkflowPalette, { type PaletteNode } from "../components/WorkflowPalette";
import NodeInspector from "../components/NodeInspector";
import BuilderToolbar from "../components/BuilderToolbar";
import RunDetailPage from "../../../pages/RunDetailPage";
import {
  MetadataModal,
  PublishModal,
} from "./WorkflowBuilderModals";
import { useRunSseSync } from "../../../hooks/useRunSseSync";
import { useRunActions } from "../hooks/useRunActions";
import { useBuilderPanels } from "../hooks/useBuilderPanels";
import { useWorkflowDraft } from "../hooks/useWorkflowDraft";
import GraphSwitcher from "../components/GraphSwitcher";
import RunsInspectorPanel from "../components/RunsInspectorPanel";
import BuilderLayout from "../components/BuilderLayout";
import type { RunStatusModel } from "../../../services/runs";
import { useAuthStore } from "@store/authSlice";
import { useToolbarStore } from "../hooks/useToolbar";
import {
  ensurePersistableIds,
} from "../utils/builderHelpers";
import { useRunsStore } from "../../../store";

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

type RunMessage =
  | { type: "success"; runId?: string; text: string }
  | { type: "error"; text: string };

const WorkflowBuilderPage = () => {
  const navigate = useNavigate();
  const { workflowId } = useParams<{ workflowId: string }>();

  const subgraphDrafts = useWorkflowStore((state) => state.subgraphDrafts);
  const activeGraph = useWorkflowStore((state) => state.activeGraph);
  const setActiveGraph = useWorkflowStore((state) => state.setActiveGraph);
  const addNodeFromTemplate = useWorkflowStore((state) => state.addNodeFromTemplate);
  const inlineSubgraph = useWorkflowStore((state) => state.inlineSubgraphIntoActiveGraph);
  const undo = useWorkflowStore((state) => state.undo);
  const redo = useWorkflowStore((state) => state.redo);
  const canUndo = useWorkflowStore((state) => state.canUndo);
  const canRedo = useWorkflowStore((state) => state.canRedo);
  const toWorkflowDefinition = useCallback(
    (draft: WorkflowDraft) => composeWorkflowDefinition(draft, subgraphDrafts),
    [subgraphDrafts]
  );
  const canEditWorkflow = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));

  const [catalogQuery, setCatalogQuery] = useState("");
  const [selectedPackageName, setSelectedPackageName] = useState<string>();
  const [runMessage, setRunMessage] = useState<RunMessage | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | undefined>();
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const {
    isPaletteOpen,
    isInspectorOpen,
    activePaletteTab,
    activeInspectorTab,
    paletteWidth,
    inspectorWidth,
    handlePaletteTabSelect,
    handleInspectorTabSelect,
    handleResizeStart,
  } = useBuilderPanels();
  const {
    workflow,
    workflowKey,
    workflowQuery,
    queryError,
    persistWorkflowMutation,
    publishWorkflowMutation,
    notFound,
    loadError,
    ownedWorkflowPackages,
    canTargetExistingPackage,
    workflowPackagesQuery,
    workflowPackagesErrorMessage,
    publishForm,
    setPublishForm,
    publishModalError,
    publishMessage,
    saveMessage,
    isPublishValid,
    handleSaveWorkflow,
    isPublishModalOpen,
    openPublishModal,
    closePublishModal,
    handlePublishModeChange,
    handleSlugInputChange,
    handlePackageSelectionChange,
    createPublishSubmitHandler,
    isMetadataModalOpen,
    openMetadataModal,
    closeMetadataModal,
    metadataForm,
    setMetadataForm,
    handleMetadataSubmit,
  } = useWorkflowDraft(workflowId, ensurePersistableIds);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [activeRunStatus, setActiveRunStatus] = useState<RunStatusModel | undefined>();
  const [isStartingRun, setIsStartingRun] = useState(false);
  const [pendingCancelId, setPendingCancelId] = useState<string | null>(null);
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
        // Defer to next tick so the UI can switch back to the root view before inlining.
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

  const catalogSearchQuery = useCatalogSearch(
    {
      q: catalogQuery.trim() || "*",
      package: selectedPackageName || undefined,
    },
    { enabled: Boolean(catalogQuery) },
  );
  const startRun = useRunsStore((state) => state.startRun);
  const cancelRun = useRunsStore((state) => state.cancelRun);
  const setToolbar = useToolbarStore((state) => state.setContent);

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

  const catalogNodes = catalogSearchQuery.data?.items ?? [];
  const availableCatalogPackages = useMemo(
    () => Array.from(new Set(catalogNodes.map((node) => node.packageName))).sort(),
    [catalogNodes]
  );
  const catalogError = catalogSearchQuery.isError
    ? (catalogSearchQuery.error as Error)
    : undefined;
  const catalogIsLoading = catalogSearchQuery.isLoading && !catalogSearchQuery.data;
  const canPublishWorkflow = canEditWorkflow && Boolean(workflowKey);
  const openPublishModalGuard = useCallback(
    () => openPublishModal(canPublishWorkflow),
    [canPublishWorkflow, openPublishModal]
  );

  const handlePublishSubmit = useMemo(
    () => createPublishSubmitHandler(captureCanvasPreview, canPublishWorkflow),
    [captureCanvasPreview, canPublishWorkflow, createPublishSubmitHandler]
  );

  const handleSelectPackage = useCallback((packageName?: string) => {
    setSelectedPackageName(packageName || undefined);
  }, []);

  useEffect(() => {
    if (!availableCatalogPackages.length) {
      if (selectedPackageName) {
        setSelectedPackageName(undefined);
      }
      return;
    }
    if (selectedPackageName && !availableCatalogPackages.includes(selectedPackageName)) {
      setSelectedPackageName(undefined);
    }
  }, [availableCatalogPackages, selectedPackageName]);

  const catalogNodeIndex = useMemo(() => {
    const index = new Map<string, CatalogNode>();
    catalogNodes.forEach((node) => {
      index.set(`${node.packageName}::${node.type}`, node);
    });
    return index;
  }, [catalogNodes]);

  const paletteItems = useMemo<PaletteNode[]>(
    () =>
      catalogNodes
        .filter((node) => !selectedPackageName || node.packageName === selectedPackageName)
        .map((node) => ({
          type: node.type ?? "",
          label: node.label ?? node.type ?? "",
          category: node.category ?? "uncategorised",
          role: node.role,
          description: node.description,
          tags: node.tags,
          status: node.status,
          packageName: node.packageName ?? "",
          defaultVersion: node.defaultVersion ?? node.latestVersion,
          latestVersion: node.latestVersion,
          versions: (node.versions ?? []).map((version) => ({
            version: version.version,
            status: version.status
          }))
        })),
    [catalogNodes, selectedPackageName]
  );

  const handleNodeDrop = useCallback(
    async (
      payload: { type: string; packageName?: string; packageVersion?: string },
      position: XYPosition
    ) => {
      try {
        const packageName = payload.packageName;
        if (!packageName) {
          throw new Error("Missing package selection for dropped node");
        }
        const catalogNode = catalogNodeIndex.get(`${packageName}::${payload.type}`);
        if (!catalogNode) {
          throw new Error(`Catalog entry for "${payload.type}" is missing`);
        }
        const preferredVersion =
          payload.packageVersion ??
          catalogNode.defaultVersion ??
          catalogNode.latestVersion ??
          catalogNode.versions?.[0]?.version;
        if (!preferredVersion) {
          throw new Error(`No version available for node "${payload.type}"`);
        }
        const versionMatch =
          catalogNode.versions?.find((version) => version.version === preferredVersion) ??
          catalogNode.versions?.[0];
        if (!versionMatch?.template) {
          throw new Error(
            `Node template for "${payload.type}" (version ${preferredVersion}) is missing`
          );
        }
        const paletteNode: WorkflowPaletteNode = {
          template: versionMatch.template,
          packageName: catalogNode.packageName,
          packageVersion: versionMatch.version
        };
        addNodeFromTemplate(paletteNode, position);
      } catch (error) {
        console.error(`Failed to create node for type ${payload.type}`, error);
      }
    },
    [addNodeFromTemplate, catalogNodeIndex]
  );

  const handleSaveWorkflowAction = useCallback(
    () => handleSaveWorkflow(workflow, captureCanvasPreview, workflowKey, getErrorMessage),
    [captureCanvasPreview, getErrorMessage, handleSaveWorkflow, workflow, workflowKey]
  );

  const { handleRunWorkflow, handleCancelActiveRun } = useRunActions({
    workflow,
    workflowKey,
    canEditWorkflow,
    activeRunId,
    toWorkflowDefinition,
    ensurePersistableIds,
    startRun: async (payload) => {
      setIsStartingRun(true);
      try {
        return await startRun(payload);
      } finally {
        setIsStartingRun(false);
      }
    },
    cancelRun: async (runId) => {
      setPendingCancelId(runId);
      try {
        await cancelRun(runId);
      } finally {
        setPendingCancelId(null);
      }
    },
    onRunMessage: setRunMessage,
    onActiveRunId: setActiveRunId,
    onActiveRunStatus: setActiveRunStatus,
    getErrorMessage,
  });

  useEffect(() => {
    if (!activeRunId) {
      setActiveRunStatus(undefined);
    }
  }, [activeRunId]);

  useRunSseSync({
    activeRunId,
    activeRunStatus,
    onActiveRunChange: setActiveRunId,
    onRunStatusChange: setActiveRunStatus,
    onRunMessage: setRunMessage,
  });

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
          {queryError?.message ?? "An unexpected error occurred."}
        </p>
        <button className="btn" type="button" onClick={() => workflowKey && workflowQuery.refetch()}>
          Retry
        </button>
      </div>
    );
  }

  const publishInProgress = publishWorkflowMutation.isPending;

  const builderToolbar = useMemo(() => {
    if (!workflow) {
      return null;
    }
    const alertMessages = [
      saveMessage
        ? (
          <span
            className={`builder-alert builder-alert--${saveMessage.type}`}
            role={saveMessage.type === "error" ? "alert" : "status"}
          >
            {saveMessage.text}
          </span>
        ) : null,
      publishMessage
        ? (
          <span
            className={`builder-alert builder-alert--${publishMessage.type}`}
            role={publishMessage.type === "error" ? "alert" : "status"}
          >
            {publishMessage.text}
          </span>
        ) : null,
      runMessage
        ? (
          <span
            className={`builder-alert builder-alert--${runMessage.type}`}
            role={runMessage.type === "error" ? "alert" : "status"}
          >
            {runMessage.text}
          </span>
        ) : null,
    ].filter(Boolean) as React.ReactNode[];

    return (
      <BuilderToolbar
        canEditWorkflow={canEditWorkflow}
        canPublishWorkflow={canPublishWorkflow}
        persistPending={persistWorkflowMutation.isPending}
        startRunPending={isStartingRun}
        cancelRunPending={Boolean(pendingCancelId)}
        cancelRunId={pendingCancelId ?? undefined}
        activeRunId={activeRunId}
        activeRunStatus={activeRunStatus}
        messages={alertMessages}
        onSave={handleSaveWorkflowAction}
        onPublish={openPublishModalGuard}
        onRun={handleRunWorkflow}
        onCancelRun={handleCancelActiveRun}
      />
    );
  }, [
    activeRunId,
    activeRunStatus,
    canEditWorkflow,
    canPublishWorkflow,
    pendingCancelId,
    handleCancelActiveRun,
    handleRunWorkflow,
    handleSaveWorkflowAction,
    openPublishModalGuard,
    persistWorkflowMutation.isPending,
    publishMessage,
    runMessage,
    saveMessage,
    isStartingRun,
    workflow
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

  const paletteHandleStyle = { left: `calc(1.5rem + ${paletteWidth}px - 0.4rem)` };
  const inspectorHandleStyle = { right: `calc(1.5rem + ${inspectorWidth}px - 0.4rem)` };
  const paletteSwitchStyle = {
    left: isPaletteOpen ? `calc(${paletteWidth}px + 3rem)` : "1.25rem"
  };
  const inspectorSwitchStyle = {
    right: isInspectorOpen ? `calc(${inspectorWidth}px + 3rem)` : "1.25rem"
  };

  const paletteTabs = (
    <>
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
    </>
  );

  const palettePanel = activePaletteTab === "catalog" ? (
    canEditWorkflow ? (
      <WorkflowPalette
        query={catalogQuery}
        onQueryChange={setCatalogQuery}
        packageOptions={availableCatalogPackages}
        selectedPackageName={selectedPackageName}
        onSelectPackage={handleSelectPackage}
        nodes={paletteItems}
        isLoading={catalogIsLoading}
        error={catalogError}
        onRetry={() => catalogSearchQuery.refetch()}
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
      canEdit={canEditWorkflow}
      workflowMetadata={workflow.metadata}
      onEditMetadata={openMetadataModal}
      onSelect={setActiveGraph}
      onInline={handleInlineFromSwitcher}
      inlineMessage={inlineMessage}
    />
  );

  const inspectorTabs = (
    <>
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
    </>
  );

  const inspectorPanel = activeInspectorTab === "inspector" ? (
    <NodeInspector />
  ) : (
    <RunsInspectorPanel onSelectRun={setSelectedRunId} />
  );

  const canvasNode = (
    <ReactFlowProvider>
      <WorkflowCanvas onNodeDrop={canEditWorkflow ? handleNodeDrop : undefined} />
    </ReactFlowProvider>
  );

  return (
    <WidgetRegistryProvider>
      <>
        <BuilderLayout
          palette={palettePanel}
          inspector={inspectorPanel}
          canvas={canvasNode}
          canvasRef={canvasRef}
          watermarkTitle={workflow.metadata?.name ?? "Untitled Workflow"}
          watermarkSubtitle={`ID: ${workflow.id}`}
          paletteWidth={paletteWidth}
          inspectorWidth={inspectorWidth}
          isPaletteOpen={isPaletteOpen}
          isInspectorOpen={isInspectorOpen}
          paletteSwitchStyle={paletteSwitchStyle}
          inspectorSwitchStyle={inspectorSwitchStyle}
          paletteHandleStyle={paletteHandleStyle}
          inspectorHandleStyle={inspectorHandleStyle}
          onPaletteResizeStart={handleResizeStart("palette")}
          onInspectorResizeStart={handleResizeStart("inspector")}
          paletteTabs={paletteTabs}
          inspectorTabs={inspectorTabs}
        />
        {selectedRunId && (
          <RunDetailPage runIdOverride={selectedRunId} onClose={() => setSelectedRunId(null)} />
        )}
        <MetadataModal
          isOpen={isMetadataModalOpen}
          form={metadataForm}
          onClose={closeMetadataModal}
          onSubmit={handleMetadataSubmit}
          onChange={(changes) => setMetadataForm((prev) => ({ ...prev, ...changes }))}
        />
        <PublishModal
          isOpen={isPublishModalOpen}
          form={publishForm}
          isValid={isPublishValid}
          canTargetExistingPackage={canTargetExistingPackage}
          ownedWorkflowPackages={ownedWorkflowPackages}
          workflowPackagesErrorMessage={workflowPackagesErrorMessage}
          isLoadingPackages={workflowPackagesQuery.isLoading}
          publishInProgress={publishInProgress}
          errorMessage={publishModalError}
          onClose={closePublishModal}
          onSubmit={handlePublishSubmit}
          onModeChange={handlePublishModeChange}
          onPackageSelect={handlePackageSelectionChange}
          onSlugChange={handleSlugInputChange}
          onFormChange={(changes) => setPublishForm((prev) => ({ ...prev, ...changes }))}
        />
      </>
    </WidgetRegistryProvider>
  );
};

export default WorkflowBuilderPage;
