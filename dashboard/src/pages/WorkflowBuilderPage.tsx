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
  useListWorkflowPackages,
  usePersistWorkflow,
  usePublishWorkflow,
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
import { useAuthStore } from "../features/auth/store";
import { useToolbarStore } from "../features/workflow/hooks/useToolbar";

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
  const addNodeFromTemplate = useWorkflowStore((state) => state.addNodeFromTemplate);
  const updateNodeStates = useWorkflowStore((state) => state.updateNodeStates);
  const hasHydrated = useRef(false);

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
      payload.previewImage = previewImage;
      setPreviewImage(previewImage);
    }

    publishWorkflowMutation.mutate(
      {
        workflowId: workflow.id,
        data: payload
      },
      {
        onSuccess: (response) => {
          const versionLabel = response.data?.version ?? publishForm.version.trim();
          setPublishMessage({
            type: "success",
            text: `Workflow published as version ${versionLabel}.`
          });
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
      workflowForPersist.previewImage = previewImage;
    }
    const definition = workflowDraftToDefinition(workflowForPersist);
    persistWorkflowMutation.mutate(
      { data: definition },
      {
        onSuccess: (response) => {
          const workflowIdResponse = response.data?.workflowId ?? workflowForPersist.id;
          setSaveMessage({ type: "success", text: "Workflow saved successfully." });
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
    if (!canEditWorkflow) {
      setRunMessage({
        type: "error",
        text: "You do not have permission to run workflows. Request workflow.editor access.",
      });
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
  }, [startRun, workflow, canEditWorkflow]);

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
              className="btn"
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
              className="btn"
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
            className="btn btn--primary"
            type="button"
            onClick={handleRunWorkflow}
            disabled={!canEditWorkflow || startRun.isPending}
          >
            <span className="btn__icon" aria-hidden="true">
              <IconRun />
            </span>
            {startRun.isPending ? "Launching..." : "Run"}
          </button>
        </div>
      </div>
    );
  }, [
    canEditWorkflow,
    handleRunWorkflow,
    handleSaveWorkflow,
    openPublishModal,
    persistWorkflowMutation.isPending,
    runMessage,
    saveMessage,
    publishMessage,
    canPublishWorkflow,
    startRun.isPending,
    workflow
  ]);

  useEffect(() => {
    setToolbar(builderToolbar);
    return () => setToolbar(null);
  }, [builderToolbar, setToolbar]);

  if (!workflow) {
    return <div className="card">Initializing builder...</div>;
  }

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

            <button
              className="builder-flyout-toggle builder-flyout-toggle--left"
              type="button"
              onClick={() => setPaletteOpen((value) => !value)}
              aria-pressed={isPaletteOpen}
            >
              {isPaletteOpen ? "Hide catalog" : "Show catalog"}
            </button>
            <button
              className="builder-flyout-toggle builder-flyout-toggle--right"
              type="button"
              onClick={() => setInspectorOpen((value) => !value)}
              aria-pressed={isInspectorOpen}
            >
              {isInspectorOpen ? "Hide inspector" : "Show inspector"}
            </button>

            <div
              className={`builder-flyout builder-flyout--palette card card--surface ${
                isPaletteOpen ? "is-open" : "is-collapsed"
              }`}
            >
              {canEditWorkflow ? (
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
                <div className="text-subtle">
                  Viewer role detected. Palette editing is disabled until you obtain workflow.editor access.
                </div>
              )}
            </div>

            <div
              className={`builder-flyout builder-flyout--inspector card card--surface ${
                isInspectorOpen ? "is-open" : "is-collapsed"
              }`}
            >
              <NodeInspector />
            </div>
          </div>
          <div className="builder-stage__watermark">
            <span className="builder-watermark__title">{workflow.metadata?.name ?? "Untitled Workflow"}</span>
            <span className="builder-watermark__subtitle">ID: {workflow.id}</span>
          </div>
        </div>
      </section>
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






