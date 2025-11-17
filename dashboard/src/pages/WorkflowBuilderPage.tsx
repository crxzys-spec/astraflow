import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ReactFlowProvider } from "reactflow";
import {
  getGetPackageQueryOptions,
  useGetPackage,
  useGetWorkflow,
  useListPackages,
  useStartRun
} from "../api/endpoints";
import type { StartRunMutationError } from "../api/endpoints";
import type { AxiosError } from "axios";
import { WidgetRegistryProvider, useWorkflowStore } from "../features/workflow";
import type { WorkflowNodeStateUpdateMap } from "../features/workflow";
import { workflowDraftToDefinition } from "../features/workflow/utils/converters";
import type { WorkflowDefinition, WorkflowPaletteNode, XYPosition } from "../features/workflow";
import WorkflowCanvas from "../features/workflow/components/WorkflowCanvas";
import WorkflowPalette, { type PaletteNode } from "../features/workflow/components/WorkflowPalette";
import NodeInspector from "../features/workflow/components/NodeInspector";
import { getClientSessionId } from "../lib/clientSession";
import { UiEventType } from "../api/models/uiEventType";
import type { UiEventEnvelope } from "../api/models/uiEventEnvelope";
import type { RunStatusEvent } from "../api/models/runStatusEvent";
import type { RunSnapshotEvent } from "../api/models/runSnapshotEvent";
import type { NodeStateEvent } from "../api/models/nodeStateEvent";
import type { NodeResultSnapshotEvent } from "../api/models/nodeResultSnapshotEvent";
import { sseClient } from "../lib/sseClient";
import {
  applyRunDefinitionSnapshot,
  updateRunDefinitionNodeRuntime,
  updateRunDefinitionNodeState,
} from "../lib/sseCache";

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

const WorkflowBuilderPage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { workflowId } = useParams<{ workflowId: string }>();

  const loadWorkflow = useWorkflowStore((state) => state.loadWorkflow);
  const resetWorkflow = useWorkflowStore((state) => state.resetWorkflow);
  const workflow = useWorkflowStore((state) => state.workflow);
  const addNodeFromTemplate = useWorkflowStore((state) => state.addNodeFromTemplate);
  const updateNodeStates = useWorkflowStore((state) => state.updateNodeStates);
  const hasHydrated = useRef(false);

  const [selectedPackageName, setSelectedPackageName] = useState<string>();
  const [selectedVersion, setSelectedVersion] = useState<string>();
  const [runMessage, setRunMessage] = useState<RunMessage | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | undefined>();
  const activeRunRef = useRef<string | undefined>();

  const isNewSession = !workflowId || workflowId === "new";
  const workflowKey = !isNewSession ? workflowId : undefined;

  const workflowQuery = useGetWorkflow(workflowKey ?? "", {
    query: { enabled: Boolean(workflowKey) }
  });

  const packagesQuery = useListPackages({
    query: { staleTime: STALE_TIME_MS }
  });

  const startRun = useStartRun(undefined, queryClient);

  const packageSummaries = packagesQuery.data?.data?.items ?? [];

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

    if (!hasHydrated.current || !workflow || workflow.id !== definition.id) {
      loadWorkflow(definition);
      hasHydrated.current = true;
      return;
    }

    const updates: WorkflowNodeStateUpdateMap = {};
    (definition.nodes ?? []).forEach((node) => {
      if (node.state != null) {
        updates[node.id] = node.state;
      }
    });
    if (Object.keys(updates).length > 0) {
      updateNodeStates(updates);
    }
  }, [workflowQuery.data, workflow, loadWorkflow, updateNodeStates]);

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
    const definition = workflowDraftToDefinition(workflow);
    setRunMessage(null);

    const clientSessionId = getClientSessionId();
    startRun.mutate(
      { data: { clientId: clientSessionId, workflow: definition } },
      {
        onSuccess: (result) => {
          const run = result.data;
          const runId = run?.runId;
          if (runId) {
            const storeSnapshot = useWorkflowStore.getState();
            storeSnapshot.resetRunState();
            activeRunRef.current = runId;
            setActiveRunId(runId);
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
  }, [startRun, workflow]);

  useEffect(() => {
    activeRunRef.current = activeRunId;
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

  if (!workflow) {
    return <div className="card">Initializing builder...</div>;
  }

  const packagesError = packagesQuery.isError ? (packagesQuery.error as Error) : undefined;
  const packageDetailError = packageDetailQuery.isError
    ? (packageDetailQuery.error as Error)
    : undefined;

  return (
    <WidgetRegistryProvider>
      <section className="builder-screen">
        <header className="builder-toolbar card">
          <div className="builder-meta">
            <span className="builder-meta__title">{workflow.metadata?.name ?? "Untitled Workflow"}</span>
            <span className="builder-meta__subtitle">ID: {workflow.id}</span>
          </div>
          <div className="builder-actions">
            {runMessage && (
              <span
                className={`builder-alert builder-alert--${runMessage.type}`}
                role={runMessage.type === "error" ? "alert" : "status"}
              >
                {runMessage.text}
              </span>
            )}
            <button
              className="btn btn--primary"
              type="button"
              onClick={handleRunWorkflow}
              disabled={startRun.isPending}
            >
              {startRun.isPending ? "Launching..." : "Run Workflow"}
            </button>
          </div>
        </header>

        <div className="builder-grid">
          <div className="builder-panel card card--surface">
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
          </div>

          <div className="builder-canvas card card--canvas">
            <ReactFlowProvider>
              <WorkflowCanvas onNodeDrop={handleNodeDrop} />
            </ReactFlowProvider>
          </div>

          <div className="builder-inspector card card--surface">
            <NodeInspector />
          </div>
        </div>
      </section>
    </WidgetRegistryProvider>
  );
};

export default WorkflowBuilderPage;




