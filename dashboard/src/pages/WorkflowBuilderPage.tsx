import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  getGetPackageQueryOptions,
  useGetPackage,
  useGetWorkflow,
  useListPackages
} from "../api/endpoints";
import { WidgetRegistryProvider, useWorkflowStore } from "../features/workflow";
import type { WorkflowPaletteNode, XYPosition } from "../features/workflow";
import WorkflowCanvas from "../features/workflow/components/WorkflowCanvas";
import WorkflowPalette from "../features/workflow/components/WorkflowPalette";
import type { PaletteNode } from "../features/workflow/components/WorkflowPalette";
import NodeInspector from "../features/workflow/components/NodeInspector";

const STALE_TIME_MS = 5 * 60_000;

const WorkflowBuilderPage = () => {
  const { workflowId } = useParams<{ workflowId: string }>();
  const loadWorkflow = useWorkflowStore((state) => state.loadWorkflow);
  const resetWorkflow = useWorkflowStore((state) => state.resetWorkflow);
  const workflow = useWorkflowStore((state) => state.workflow);
  const addNodeFromTemplate = useWorkflowStore((state) => state.addNodeFromTemplate);
  const queryClient = useQueryClient();
  const [selectedPackageName, setSelectedPackageName] = useState<string>();
  const [selectedVersion, setSelectedVersion] = useState<string>();

  const workflowQuery = useGetWorkflow(workflowId ?? "", {
    query: {
      enabled: Boolean(workflowId)
    }
  });

  const packagesQuery = useListPackages({
    query: {
      staleTime: STALE_TIME_MS
    }
  });

  const packageSummaries = packagesQuery.data?.data?.items ?? [];

  const handleSelectPackage = useCallback(
    (packageName: string) => {
      setSelectedPackageName(packageName);
      const summary = packageSummaries.find((item) => item.name === packageName);
      const preferredVersion = summary
        ? summary.defaultVersion ?? summary.latestVersion ?? summary.versions?.[0]
        : undefined;
      setSelectedVersion(preferredVersion);
    },
    [packageSummaries]
  );

  const handleSelectVersion = useCallback((version: string) => {
    setSelectedVersion(version || undefined);
  }, []);

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
      const preferredVersion = first.defaultVersion ?? first.latestVersion ?? first.versions?.[0];
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
      query: {
        enabled: Boolean(selectedPackageName),
        staleTime: STALE_TIME_MS
      }
    }
  );

  useEffect(() => {
    if (workflowQuery.data?.data) {
      loadWorkflow(workflowQuery.data.data);
    }
  }, [workflowQuery.data, loadWorkflow]);

  useEffect(() => () => resetWorkflow(), [resetWorkflow]);

  const manifestNodes = packageDetailQuery.data?.data?.manifest?.nodes ?? [];

  const paletteItems = useMemo<PaletteNode[]>(
    () =>
      manifestNodes.map((node) => ({
        type: node.type,
        label: node.label,
        category: node.category,
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

  if (!workflowId) {
    return <div className="card">Workflow ID is missing.</div>;
  }

  if (workflowQuery.isLoading) {
    return <div className="card">Loading workflow...</div>;
  }

  if (workflowQuery.isError) {
    return (
      <div className="card">
        <p className="error">Failed to load workflow: {(workflowQuery.error as Error).message}</p>
      </div>
    );
  }

  if (!workflow) {
    return <div className="card">Workflow not available.</div>;
  }

  const packagesError = packagesQuery.isError ? (packagesQuery.error as Error) : undefined;
  const packageDetailError = packageDetailQuery.isError
    ? (packageDetailQuery.error as Error)
    : undefined;

  return (
    <div className="workflow-builder stack">
      <div className="card">
        <h2>{workflow.metadata?.name ?? "Workflow Builder"}</h2>
        <p className="text-subtle">ID: {workflow.id}</p>
      </div>
      <WidgetRegistryProvider>
        <div className="workflow-builder__body">
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
          <div className="card workflow-canvas-card">
            <WorkflowCanvas onNodeDrop={handleNodeDrop} />
          </div>
          <NodeInspector />
        </div>
      </WidgetRegistryProvider>
    </div>
  );
};

export default WorkflowBuilderPage;
