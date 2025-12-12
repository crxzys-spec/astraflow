import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { AxiosError } from "axios";
import { useNavigate } from "react-router-dom";
import type { QueryClient } from "@tanstack/react-query";
import {
  useGetWorkflow,
  usePersistWorkflow,
  usePublishWorkflow,
  useSetWorkflowPreview,
  useListWorkflowPackages,
} from "../api/endpoints";
import { useWorkflowStore } from "../features/workflow";
import { workflowDraftToDefinition } from "../features/workflow/utils/converters";
import type {
  WorkflowDraft,
  WorkflowNodeStateUpdateMap,
} from "../features/workflow";
import { createEmptyWorkflow, normalizeVisibility, slugifyValue } from "../features/workflow/utils/builderHelpers";

export type PublishMessage = { type: "success" | "error"; text: string };
export type MetadataFormState = { name: string; description: string };
export type PublishFormState = {
  version: string;
  displayName: string;
  summary: string;
  visibility: "private" | "public" | "internal";
  changelog: string;
  mode: "new" | "existing";
  slug: string;
  packageId: string;
};

export const useWorkflowDraft = (
  workflowId: string | undefined,
  queryClient: QueryClient,
  ensurePersistableIds: (draft: WorkflowDraft, workflowKey?: string) => WorkflowDraft,
) => {
  const navigate = useNavigate();
  const loadWorkflow = useWorkflowStore((state) => state.loadWorkflow);
  const resetWorkflow = useWorkflowStore((state) => state.resetWorkflow);
  const setPreviewImage = useWorkflowStore((state) => state.setPreviewImage);
  const updateWorkflowMetadata = useWorkflowStore((state) => state.updateWorkflowMetadata);
  const workflow = useWorkflowStore((state) => state.workflow);
  const subgraphDrafts = useWorkflowStore((state) => state.subgraphDrafts);
  const updateNodeStates = useWorkflowStore((state) => state.updateNodeStates);
  const hasHydrated = useRef(false);
  const lastHydrateAt = useRef<number>(0);

  const isNewSession = !workflowId || workflowId === "new";
  const workflowKey = !isNewSession ? workflowId : undefined;

  const workflowQuery = useGetWorkflow(workflowKey ?? "new", {
    query: { enabled: Boolean(workflowKey) },
  });
  const persistWorkflowMutation = usePersistWorkflow(undefined, queryClient);
  const publishWorkflowMutation = usePublishWorkflow(undefined, queryClient);
  const setPreviewMutation = useSetWorkflowPreview(undefined, queryClient);
  const workflowPackagesQuery = useListWorkflowPackages(undefined, { query: { enabled: true } }, queryClient);

  const [publishMessage, setPublishMessage] = useState<PublishMessage | null>(null);
  const [saveMessage, setSaveMessage] = useState<PublishMessage | null>(null);
  const [publishForm, setPublishForm] = useState<PublishFormState>({
    version: "",
    displayName: "",
    summary: "",
    visibility: "private" as const,
    changelog: "",
    mode: "new" as const,
    slug: "",
    packageId: ""
  });
  const [slugEdited, setSlugEdited] = useState(false);
  const [publishModalError, setPublishModalError] = useState<string | null>(null);
  const [isPublishModalOpen, setPublishModalOpen] = useState(false);
  const [isMetadataModalOpen, setMetadataModalOpen] = useState(false);
  const [metadataForm, setMetadataForm] = useState<MetadataFormState>({ name: "", description: "" });

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
    const definition = workflowQuery.data;
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

  const openMetadataModal = useCallback(() => {
    if (!workflow) {
      return;
    }
    setMetadataForm({
      name: workflow.metadata?.name ?? "",
      description: workflow.metadata?.description ?? "",
    });
    setMetadataModalOpen(true);
  }, [workflow]);

  const closeMetadataModal = useCallback(() => {
    setMetadataModalOpen(false);
  }, []);

  const handleMetadataSubmit = useCallback(
    (event?: FormEvent<HTMLFormElement>) => {
      event?.preventDefault();
      if (!workflow) {
        return;
      }
      updateWorkflowMetadata({
        name: metadataForm.name.trim() || undefined,
        description: metadataForm.description.trim() || undefined,
      });
      setMetadataModalOpen(false);
    },
    [metadataForm.description, metadataForm.name, updateWorkflowMetadata, workflow]
  );

  const handleSaveWorkflow = useCallback(
    async (
      workflow: WorkflowDraft | undefined,
      capturePreview: () => Promise<string | null | undefined>,
      workflowKey?: string,
      getErrorMessage?: (error: unknown) => string,
    ) => {
      if (!workflow) {
        setSaveMessage({ type: "error", text: "Workflow is not loaded." });
        return;
      }
      const workflowForPersist = ensurePersistableIds(workflow, workflowKey);
      const previewImage = (await capturePreview()) ?? workflow.previewImage ?? undefined;
      if (previewImage) {
        setPreviewImage(previewImage);
      }
      const definition = workflowDraftToDefinition(workflowForPersist);
      persistWorkflowMutation.mutate(
        { data: definition },
        {
          onSuccess: async (response) => {
            const workflowIdResponse = response.data?.workflowId ?? workflowForPersist.id;
            setSaveMessage({ type: "success", text: "Workflow saved successfully." });
            if (workflowIdResponse) {
              await setPreviewMutation.mutateAsync({
                workflowId: workflowIdResponse,
                data: { previewImage },
              });
            }
            if (!workflowKey || workflowKey !== workflowIdResponse) {
              navigate(`/workflows/${workflowIdResponse}`, { replace: true });
            } else {
              queryClient.invalidateQueries({ queryKey: ["/api/v1/workflows", workflowIdResponse] });
              queryClient.invalidateQueries({ queryKey: ["/api/v1/workflows"] });
            }
          },
          onError: (error) => {
            setSaveMessage({ type: "error", text: getErrorMessage ? getErrorMessage(error) : "Failed to save" });
          }
        }
      );
    },
    [ensurePersistableIds, navigate, persistWorkflowMutation, queryClient, setPreviewImage, setPreviewMutation]
  );

  const uploadPreview = useCallback(
    async (workflowId: string, preview?: string | null) => {
      if (!preview) return;
      try {
        await setPreviewMutation.mutateAsync({
          workflowId,
          data: { previewImage: preview },
        });
      } catch (error) {
        console.warn("Failed to upload workflow preview", error);
      }
    },
    [setPreviewMutation]
  );

  const ownedWorkflowPackages = (workflowPackagesQuery.data?.items ?? []).filter((pkg) => pkg.owner === "me");
  const canTargetExistingPackage = ownedWorkflowPackages.length > 0;
  const workflowPackagesErrorMessage =
    workflowPackagesQuery.isError && workflowPackagesQuery.error
      ? (workflowPackagesQuery.error as AxiosError)?.message ?? "Failed to load packages"
      : null;

  const derivedSlugForValidation = publishForm.mode === "new"
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
    (publishForm.mode === "existing" ? Boolean(publishForm.packageId) : Boolean(derivedSlugForValidation));

  const closePublishModal = useCallback(() => {
    if (publishWorkflowMutation.isPending) {
      return;
    }
    setPublishModalOpen(false);
    setSlugEdited(false);
  }, [publishWorkflowMutation.isPending]);

  const openPublishModal = useCallback(
    (canPublishWorkflow: boolean) => {
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
    },
    [ownedWorkflowPackages, setPublishForm, setSlugEdited, setPublishModalError, workflow]
  );

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

  const handlePublishModeChange = useCallback(
    (mode: PublishFormState["mode"]) => {
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
    },
    [ownedWorkflowPackages, workflow]
  );

  const handleSlugInputChange = useCallback((value: string) => {
    setSlugEdited(Boolean(value));
    setPublishForm((prev) => ({ ...prev, slug: slugifyValue(value) }));
  }, []);

  const handlePackageSelectionChange = useCallback(
    (packageId: string) => {
      const selected = ownedWorkflowPackages.find((pkg) => pkg.id === packageId);
      setPublishForm((prev) => ({
        ...prev,
        packageId,
        displayName: selected?.displayName ?? prev.displayName,
        summary: selected?.summary ?? prev.summary,
        visibility: normalizeVisibility(selected?.visibility),
      }));
    },
    [ownedWorkflowPackages]
  );

  const createPublishSubmitHandler = useCallback(
    (
      capturePreview: () => Promise<string | null | undefined>,
      canPublishWorkflow: boolean
    ) => async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!workflow?.id || !canPublishWorkflow) {
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
        previewImage?: string | null;
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
        (await capturePreview()) ?? workflow.previewImage ?? undefined;
      if (previewImage) {
        setPreviewImage(previewImage);
      }
      payload.previewImage = previewImage ?? null;

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
            await uploadPreview(workflow.id, previewImage);
            setPublishModalOpen(false);
          },
          onError: (error) => {
            const message =
              (error as { response?: { data?: { message?: string } } }).response?.data?.message ??
              (error as Error | undefined)?.message ??
              "Failed to publish.";
            setPublishModalError(message);
          }
        }
      );
    },
    [
      publishForm.changelog,
      publishForm.displayName,
      publishForm.mode,
      publishForm.packageId,
      publishForm.slug,
      publishForm.summary,
      publishForm.version,
      publishForm.visibility,
      publishWorkflowMutation,
      setPreviewImage,
      uploadPreview,
      workflow
    ]
  );

  return {
    workflow,
    workflowKey,
    workflowQuery,
    queryError,
    persistWorkflowMutation,
    publishWorkflowMutation,
    setPreviewImage,
    updateWorkflowMetadata,
    resetWorkflow,
    notFound,
    loadError,
    ownedWorkflowPackages,
    canTargetExistingPackage,
    workflowPackagesQuery,
    workflowPackagesErrorMessage,
    publishForm,
    setPublishForm,
    slugEdited,
    setSlugEdited,
    publishModalError,
    setPublishModalError,
    publishMessage,
    setPublishMessage,
    saveMessage,
    setSaveMessage,
    isPublishValid,
    derivedSlugForValidation,
    handleSaveWorkflow,
    uploadPreview,
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
  };
};
