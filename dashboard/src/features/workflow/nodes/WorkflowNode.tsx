import clsx from "clsx";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactElement } from "react";
import type { DragEvent } from "react";
import type { NodeProps } from "reactflow";
import { Handle, Position } from "reactflow";
import { useQueryClient } from "@tanstack/react-query";
import type {
  NodePortDefinition,
  NodeWidgetDefinition,
  WorkflowDraft,
  WorkflowMiddlewareDraft,
  WorkflowNodeDraft,
} from "../types.ts";
import { useWorkflowStore } from "../store.ts";
import {
  formatBindingDisplay,
  getBindingValue,
  isBindingEditable,
  resolveBindingPath,
  resolveWidgetBinding,
  setBindingValue
} from "../utils/binding.ts";
import type { BindingResolution } from "../utils/binding.ts";
import type { JsonSchema } from "../utils/schemaDefaults.ts";
import { createNodeDraftFromTemplate } from "../utils/converters.ts";
import { UIBindingMode } from "../../../api/models/uIBindingMode";
import { useWidgetRegistry, registerBuiltinWidgets } from "../widgets";
import {
  WORKFLOW_NODE_DRAG_FORMAT,
  WORKFLOW_NODE_DRAG_PACKAGE_KEY,
  WORKFLOW_NODE_DRAG_ROLE_KEY,
  WORKFLOW_NODE_DRAG_TYPE_KEY,
  WORKFLOW_NODE_DRAG_VERSION_KEY
} from "../constants.ts";
import { getGetPackageQueryOptions } from "../../../api/endpoints";
import type { WorkflowPaletteNode } from "../types.ts";

interface WorkflowNodeData {
  nodeId: string;
  label?: string;
  status?: string;
  stage?: string;
  role?: string;
  progress?: number;
  message?: string;
  lastUpdatedAt?: string;
  packageName?: string;
  packageVersion?: string;
  adapter?: string;
  handler?: string;
  widgets?: NodeWidgetDefinition[];
  fallbackInputPorts?: string[];
  fallbackOutputPorts?: string[];
  middlewares?: WorkflowMiddlewareDraft[];
  attachedMiddlewares?: { id: string; label: string; node: WorkflowMiddlewareDraft; index: number }[];
}

registerBuiltinWidgets();

const formatPackage = (node?: WorkflowNodeData | WorkflowNodeDraft) => {
  const name = node?.packageName;
  if (!name) {
    return "-";
  }
  const version = node?.packageVersion ?? "latest";
  return `${name}@${version}`;
};

const formatStage = (stage: string): string =>
  stage
    .replace(/[\s._-]+/g, " ")
    .replace(/^\w/, (char) => char.toUpperCase());

const describeSchemaType = (schema?: JsonSchema) => {
  if (!schema) {
    return undefined;
  }
  if (Array.isArray(schema.type)) {
    return schema.type.join(" | ");
  }
  return schema.type;
};

const getSchemaInfo = (
  node: WorkflowNodeDraft | undefined,
  binding: BindingResolution | undefined
): { schema?: JsonSchema; required?: boolean } => {
  if (!node?.schema || !binding) {
    return {};
  }
  const rootSchema =
    (binding.root === "parameters" ? node.schema.parameters : node.schema.results) as JsonSchema | undefined;
  if (!rootSchema) {
    return {};
  }
  if (!binding.path.length) {
    return { schema: rootSchema, required: false };
  }
  let current: JsonSchema | undefined = rootSchema;
  let required = false;
  for (let index = 0; index < binding.path.length; index += 1) {
    const segment = binding.path[index];
    if (!current?.properties) {
      return {};
    }
    const next: JsonSchema | undefined = current.properties[segment];
    if (!next) {
      return {};
    }
    if (index === binding.path.length - 1) {
      required = Array.isArray(current.required) ? current.required.includes(segment) : false;
    }
    current = next;
  }
  return { schema: current, required };
};

const createFallbackPort = (key: string, label?: string): NodePortDefinition => ({
  key,
  label: label ?? key,
  binding: {
    path: "",
    mode: UIBindingMode.write
  }
});

const mergePorts = (
  defined: NodePortDefinition[] | undefined,
  fallbackKeys: string[] | undefined
): NodePortDefinition[] => {
  const base = defined ? [...defined] : [];
  if (!fallbackKeys?.length) {
    return base;
  }
  const seen = new Set(base.map((port) => port.key));
  fallbackKeys.forEach((key) => {
    if (!seen.has(key)) {
      base.push(createFallbackPort(key));
    }
  });
  return base;
};

const WorkflowNode = memo(({ id, data, selected }: NodeProps<WorkflowNodeData>) => {
  const nodeId = data?.nodeId ?? id;
  const rootWorkflow = useWorkflowStore((state) => state.workflow);
  const activeGraph = useWorkflowStore((state) => state.activeGraph);
  const subgraphDrafts = useWorkflowStore((state) => state.subgraphDrafts);
  const workflow: WorkflowDraft | undefined = useMemo(() => {
    if (!rootWorkflow) {
      return undefined;
    }
    if (activeGraph.type === "subgraph") {
      const subgraph = subgraphDrafts.find((entry) => entry.id === activeGraph.subgraphId)?.definition;
      return subgraph ?? rootWorkflow;
    }
    return rootWorkflow;
  }, [activeGraph, rootWorkflow, subgraphDrafts]);
  const workflowNode = workflow?.nodes[nodeId];
  const workflowEdges = workflow?.edges ?? [];
  const updateNode = useWorkflowStore((state) => state.updateNode);
  const { resolve } = useWidgetRegistry();
  const queryClient = useQueryClient();
  const setSelectedNode = useWorkflowStore((state) => state.setSelectedNode);
  const middlewareDragRef = useRef<string | null>(null);

  const displayLabel = workflowNode?.label ?? data?.label ?? nodeId;
  const status = workflowNode?.status ?? data?.status;
  const runtimeState =
    workflowNode?.state ??
    (data?.stage
      ? {
          stage: data.stage,
          progress: data.progress,
          message: data.message,
          lastUpdatedAt: data.lastUpdatedAt,
        }
      : undefined);
  const stage = runtimeState?.stage;
  const progress =
    typeof runtimeState?.progress === "number"
      ? Math.max(0, Math.min(1, runtimeState.progress))
      : undefined;
  const progressPercent =
    typeof progress === "number" ? Math.round(progress * 100) : undefined;
  const progressDisplay =
    typeof progressPercent === "number"
      ? Math.max(0, Math.min(100, progressPercent))
      : undefined;
  const filteredFallbackInputs =
    data?.fallbackInputPorts?.filter((key) => !key.startsWith("mw:")) ?? data?.fallbackInputPorts;
  const filteredFallbackOutputs =
    data?.fallbackOutputPorts?.filter((key) => !key.startsWith("mw:")) ?? data?.fallbackOutputPorts;
  const inputPorts = mergePorts(workflowNode?.ui?.inputPorts, filteredFallbackInputs);
  const outputPorts = mergePorts(workflowNode?.ui?.outputPorts, filteredFallbackOutputs);
  const widgets = workflowNode?.ui?.widgets ?? data?.widgets ?? [];
  const [connectedWidgetExpansion, setConnectedWidgetExpansion] = useState<Record<string, boolean>>({});
  const [middlewareWidgetExpansion, setMiddlewareWidgetExpansion] = useState<Record<string, boolean>>({});
  const [draggingMiddlewareId, setDraggingMiddlewareId] = useState<string | null>(null);
  const [hoverMiddlewareId, setHoverMiddlewareId] = useState<string | null>(null);
  const isMiddlewareNode = (workflowNode?.role ?? data?.role) === "middleware";
  const attachedMiddlewares =
    (!isMiddlewareNode ? data?.attachedMiddlewares ?? [] : []) ?? [];

  const reorderMiddleware = useCallback(
    (hostId: string, sourceId: string, targetId: string) => {
      if (!hostId || sourceId === targetId) {
        return;
      }
      updateNode(hostId, (current) => {
        const list = current.middlewares ? [...current.middlewares] : [];
        const from = list.findIndex((mw) => mw.id === sourceId);
        const to = list.findIndex((mw) => mw.id === targetId);
        if (from === -1 || to === -1 || from === to) {
          return current;
        }
        const [item] = list.splice(from, 1);
        list.splice(to, 0, item);
        return { ...current, middlewares: list };
      });
    },
    [updateNode]
  );

  const removeMiddleware = useCallback(
    (hostId: string, middlewareId: string) => {
      updateNode(hostId, (current) => {
        const next = (current.middlewares ?? []).filter((mw) => mw.id !== middlewareId);
        return { ...current, middlewares: next };
      });
    },
    [updateNode]
  );

  const middlewareInputPorts = useMemo(() => {
    if (isMiddlewareNode) {
      return [];
    }
    return attachedMiddlewares.flatMap((mw) =>
      (mw.node.ui?.inputPorts ?? []).map((port) => ({
        ...port,
        key: `mw:${mw.id}:input:${port.key}`,
        label: `${mw.label ?? "Middleware"} · ${port.label ?? port.key}`,
      }))
    );
  }, [attachedMiddlewares, isMiddlewareNode]);

  const middlewareOutputPorts = useMemo(() => {
    if (isMiddlewareNode) {
      return [];
    }
    return attachedMiddlewares.flatMap((mw) =>
      (mw.node.ui?.outputPorts ?? []).map((port) => ({
        ...port,
        key: `mw:${mw.id}:output:${port.key}`,
        label: `${mw.label ?? "Middleware"} · ${port.label ?? port.key}`,
      }))
    );
  }, [attachedMiddlewares, isMiddlewareNode]);

  const displayInputPorts = useMemo(
    () => [...inputPorts, ...middlewareInputPorts],
    [inputPorts, middlewareInputPorts]
  );
  const displayOutputPorts = useMemo(
    () => [...outputPorts, ...middlewareOutputPorts],
    [outputPorts, middlewareOutputPorts]
  );

  const parameterInputBindings = useMemo(() => {
    const connected = new Set<string>();
    if (!workflowNode) {
      return connected;
    }
    const bindingByPortKey = new Map<string, string>();
    (workflowNode.ui?.inputPorts ?? []).forEach((port) => {
      const binding = resolveBindingPath(port.binding?.path ?? "");
      if (binding && binding.root === "parameters") {
        bindingByPortKey.set(port.key, `${binding.root}:${binding.path.join("/")}`);
      }
    });
    workflowEdges.forEach((edge) => {
      if (edge.target.nodeId !== nodeId || !edge.target.portId) {
        return;
      }
      const bindingKey = bindingByPortKey.get(edge.target.portId);
      if (bindingKey) {
        connected.add(bindingKey);
      }
    });
    return connected;
  }, [workflowEdges, nodeId, workflowNode]);

  useEffect(() => {
    setConnectedWidgetExpansion((previous) => {
      const next: Record<string, boolean> = {};
      parameterInputBindings.forEach((key) => {
        if (previous[key]) {
          next[key] = true;
        }
      });
      return next;
    });
  }, [parameterInputBindings]);

  const renderMiddlewareWidgets = useCallback(
    (mw: WorkflowMiddlewareDraft, hostId: string): ReactElement[] => {
      if (!mw.ui?.widgets?.length) {
        return [];
      }
      const bindingByPortKey = new Map<string, string>();
      (mw.ui?.inputPorts ?? []).forEach((port) => {
        const binding = resolveBindingPath(port.binding?.path ?? "");
        if (binding && binding.root === "parameters") {
          bindingByPortKey.set(`mw:${mw.id}:input:${port.key}`, `${binding.root}:${binding.path.join("/")}`);
        }
      });
      const connected = new Set<string>();
      workflowEdges.forEach((edge) => {
        if (edge.target.nodeId !== hostId || !edge.target.portId) {
          return;
        }
        const bindingKey = bindingByPortKey.get(edge.target.portId);
        if (bindingKey) {
          connected.add(bindingKey);
        }
      });

      return mw.ui.widgets.reduce<ReactElement[]>((acc, widget) => {
        const binding = resolveWidgetBinding(widget);
        if (!binding) {
          return acc;
        }
        const registration = resolve(widget);
        if (!registration) {
          return acc;
        }
        const value = getBindingValue(mw, binding);
        const bindingKey = `${binding.root}:${binding.path.join("/")}`;
        const coveredByInput = binding.root === "parameters" && connected.has(bindingKey);
        const readOnly =
          !isBindingEditable(widget.binding?.mode) || binding.root === "results" || coveredByInput;
        const expansionKey = `${mw.id}:${bindingKey}`;
        const isExpanded = !coveredByInput || middlewareWidgetExpansion[expansionKey] === true;

        const handleChange = (nextValue: unknown) => {
          updateNode(hostId, (current) => {
            const list = current.middlewares ? [...current.middlewares] : [];
            const index = list.findIndex((entry) => entry.id === mw.id);
            if (index === -1) {
              return current;
            }
            const nextMiddleware = setBindingValue(list[index], binding, nextValue) as WorkflowMiddlewareDraft;
            const nextList = [...list];
            nextList[index] = nextMiddleware;
            return { ...current, middlewares: nextList };
          });
        };

        acc.push(
          <div
            key={`${mw.id}-${widget.key}`}
            className={clsx("workflow-node__widget-wrapper", "workflow-node__widget-wrapper--middleware", {
              "workflow-node__widget-wrapper--upstream": coveredByInput,
            })}
          >
            {coveredByInput && (
              <div className="workflow-node__widget-meta">
                <span className="workflow-node__widget-hint">Provided by upstream connection</span>
                <button
                  type="button"
                  className="workflow-node__widget-toggle"
                  onClick={() =>
                    setMiddlewareWidgetExpansion((previous) => ({
                      ...previous,
                      [expansionKey]: !isExpanded,
                    }))
                  }
                >
                  {isExpanded ? "Hide" : "View"}
                </button>
              </div>
            )}
            {(!coveredByInput || isExpanded) && (
              <registration.component
                widget={widget}
                node={mw}
                value={value}
                onChange={handleChange}
                readOnly={readOnly}
              />
            )}
          </div>
        );
        return acc;
      }, []);
    },
    [middlewareWidgetExpansion, resolve, updateNode, workflowEdges]
  );

  const widgetElements = useMemo<ReactElement[]>(() => {
    if (!workflowNode || !widgets.length) {
      return [];
    }
    return widgets.reduce<ReactElement[]>((accumulator, widget) => {
      const binding = resolveWidgetBinding(widget);
      if (!binding) {
        return accumulator;
      }
      const registration = resolve(widget);
      if (!registration) {
        return accumulator;
      }
      const value = getBindingValue(workflowNode, binding);
      const bindingKey = `${binding.root}:${binding.path.join("/")}`;
      const coveredByInput = binding.root === "parameters" && parameterInputBindings.has(bindingKey);
      const readOnly =
        !isBindingEditable(widget.binding?.mode) || binding.root === "results" || coveredByInput;
      const isExpanded = !coveredByInput || connectedWidgetExpansion[bindingKey] === true;

      const handleChange = (nextValue: unknown) => {
        updateNode(nodeId, (current) => setBindingValue(current, binding, nextValue));
      };

      accumulator.push(
        <div
          key={widget.key}
          className={clsx("workflow-node__widget-wrapper", {
            "workflow-node__widget-wrapper--upstream": coveredByInput,
          })}
        >
          {coveredByInput && (
            <div className="workflow-node__widget-meta">
              <span className="workflow-node__widget-hint">Provided by upstream connection</span>
              <button
                type="button"
                className="workflow-node__widget-toggle"
                onClick={() =>
                  setConnectedWidgetExpansion((previous) => ({
                    ...previous,
                    [bindingKey]: !isExpanded,
                  }))
                }
              >
                {isExpanded ? "Hide" : "View"}
              </button>
            </div>
          )}
          {(!coveredByInput || isExpanded) && (
            <registration.component
              widget={widget}
              node={workflowNode}
              value={value}
              onChange={handleChange}
              readOnly={readOnly}
            />
          )}
        </div>
      );
      return accumulator;
    }, []);
  }, [
    connectedWidgetExpansion,
    nodeId,
    parameterInputBindings,
    resolve,
    updateNode,
    widgets,
    workflowNode,
  ]);

  const stageClass =
    stage && stage.length
      ? stage
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-+|-+$/g, "")
      : undefined;

  const nodeClassName = clsx("workflow-node", {
    "workflow-node--selected": selected,
    "workflow-node--middleware": isMiddlewareNode,
    ...(stageClass ? { [`workflow-node--stage-${stageClass}`]: true } : {}),
  });
  const isContainerNode = workflowNode?.nodeKind === "workflow.container";
  const canAttachMiddleware = !isMiddlewareNode;

  const handleMiddlewareDragOver = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      if (!canAttachMiddleware) {
        return;
      }
      const raw = event.dataTransfer.getData(WORKFLOW_NODE_DRAG_FORMAT);
      if (!raw) {
        return;
      }
      try {
        const payload = JSON.parse(raw) as Record<string, unknown>;
        const role = payload[WORKFLOW_NODE_DRAG_ROLE_KEY];
        if (role === "middleware") {
          event.preventDefault();
          event.dataTransfer.dropEffect = "copy";
        }
      } catch {
        // ignore malformed payloads
      }
    },
    [canAttachMiddleware]
  );

  const handleMiddlewareDrop = useCallback(
    async (event: DragEvent<HTMLDivElement>) => {
      if (!canAttachMiddleware || !workflowNode) {
        return;
      }
      const raw = event.dataTransfer.getData(WORKFLOW_NODE_DRAG_FORMAT);
      if (!raw) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      try {
        const payload = JSON.parse(raw) as Record<string, unknown>;
        if (payload[WORKFLOW_NODE_DRAG_ROLE_KEY] !== "middleware") {
          return;
        }
        const nodeType = payload[WORKFLOW_NODE_DRAG_TYPE_KEY];
        const packageName = payload[WORKFLOW_NODE_DRAG_PACKAGE_KEY];
        const packageVersion = payload[WORKFLOW_NODE_DRAG_VERSION_KEY];
        if (typeof nodeType !== "string" || typeof packageName !== "string") {
          return;
        }
        const response = await queryClient.ensureQueryData(
          getGetPackageQueryOptions(
            packageName,
            typeof packageVersion === "string" && packageVersion.length
              ? { version: packageVersion }
              : undefined,
            { query: { staleTime: 5 * 60 * 1000 } }
          )
        );
        const definition = response?.data;
        const template = definition?.manifest?.nodes?.find((node) => node.type === nodeType);
        if (!template || template.role !== "middleware") {
          return;
        }
        const paletteNode: WorkflowPaletteNode = {
          template,
          packageName: definition.name,
          packageVersion: definition.version
        };
        const draftNode = createNodeDraftFromTemplate(
          paletteNode,
          workflowNode.position ? { ...workflowNode.position } : { x: 0, y: 0 }
        );
        const { position: _mwPosition, dependencies: _mwDependencies, middlewares: _nestedMiddlewares, ...rest } =
          draftNode;
        const middlewareDraft: WorkflowMiddlewareDraft = {
          ...rest,
          role: "middleware",
        };
        updateNode(workflowNode.id, (current) => {
          const next = current.middlewares ? [...current.middlewares] : [];
          const hasExisting = next.some((entry) => entry.id === middlewareDraft.id);
          if (!hasExisting) {
            next.push(middlewareDraft);
          }
          return { ...current, middlewares: next };
        });
      } catch (error) {
        console.error("Failed to attach middleware", error);
      }
    },
    [canAttachMiddleware, queryClient, updateNode, workflowNode]
  );

  return (
    <div
      className={nodeClassName}
      onDragOver={handleMiddlewareDragOver}
      onDrop={handleMiddlewareDrop}
      style={undefined} // no dynamic height; middleware renders in its own zone
    >
      <header className="workflow-node__header">
        <span className="workflow-node__label">{displayLabel}</span>
        <div className="workflow-node__header-badges">
          {isContainerNode && (
            <span className="workflow-node__status workflow-node__status--container" title="Container node">
              Container
            </span>
          )}
          {stage && (
            <span
              className={clsx(
                "workflow-node__stage",
                stageClass ? `workflow-node__stage--${stageClass}` : undefined,
              )}
            >
              {formatStage(stage)}
              {typeof progressDisplay === "number" && (
                <span className="workflow-node__stage-progress">
                  (
                  <span className="workflow-node__stage-progress-value">
                    {progressDisplay.toString().padStart(3, "\u00a0")}
                  </span>
                  %)
                </span>
              )}
            </span>
          )}
          {status && <span className="workflow-node__status">{status}</span>}
        </div>
      </header>
        <div className="workflow-node__body">
          <div className="workflow-node__ports workflow-node__ports--inputs">
          {displayInputPorts.map((port) => {
            const binding = resolveBindingPath(port.binding?.path ?? "");
            const schemaInfo = getSchemaInfo(workflowNode, binding);
            const bindingDisplay = formatBindingDisplay(port.binding, binding);
            const title = bindingDisplay ? `${port.label} (${bindingDisplay})` : port.label;
            return (
              <div
                key={port.key}
                className="workflow-node__port workflow-node__port--input"
                title={title}
                data-binding-root={binding?.root}
                data-binding-path={bindingDisplay}
                data-schema-type={describeSchemaType(schemaInfo.schema)}
                data-required={schemaInfo.required ? "true" : undefined}
              >
                <Handle
                  id={port.key}
                  type="target"
                  position={Position.Left}
                  className="workflow-node__handle workflow-node__handle--input"
                />
                <span className="workflow-node__port-label">{port.label}</span>
              </div>
            );
          })}
        </div>
        <div className="workflow-node__content">
          <div className="workflow-node__badges">
            <span className="workflow-node__package">{formatPackage(workflowNode ?? data)}</span>
            {widgetElements.length > 0 && (
              <div
                className="workflow-node__widgets nodrag"
                onPointerDown={(event) => event.stopPropagation()}
              >
                {widgetElements}
              </div>
            )}
          </div>
        </div>
        <div className="workflow-node__ports workflow-node__ports--outputs">
          {displayOutputPorts.map((port) => {
            const binding = resolveBindingPath(port.binding?.path ?? "");
            const schemaInfo = getSchemaInfo(workflowNode, binding);
            const bindingDisplay = formatBindingDisplay(port.binding, binding);
            const title = bindingDisplay ? `${port.label} (${bindingDisplay})` : port.label;
            return (
              <div
                key={port.key}
                className="workflow-node__port workflow-node__port--output"
                title={title}
                data-binding-root={binding?.root}
                data-binding-path={bindingDisplay}
                data-schema-type={describeSchemaType(schemaInfo.schema)}
                data-required={schemaInfo.required ? "true" : undefined}
              >
                <span className="workflow-node__port-label">{port.label}</span>
                <Handle
                  id={port.key}
                  type="source"
                  position={Position.Right}
                  className="workflow-node__handle workflow-node__handle--output"
                />
              </div>
            );
          })}
        </div>
      </div>
      {!isMiddlewareNode && attachedMiddlewares.length > 0 && (
        <div className="workflow-node__middleware-zone" title="Attached middlewares">
          <div className="workflow-node__middleware-zone__header">
            <span className="workflow-node__middleware-label">Middlewares</span>
          </div>
          <div className="workflow-node__middleware-zone__list">
            {attachedMiddlewares
              .sort((a, b) => a.index - b.index)
              .map((mw) => {
                const mwStatus = mw.node.status;
                const mwWidgets = renderMiddlewareWidgets(mw.node, workflowNode?.id ?? nodeId);
                const mwInputPorts = mw.node.ui?.inputPorts ?? [];
                const mwOutputPorts = mw.node.ui?.outputPorts ?? [];
                const mwRuntimeState = mw.node.state;
                const mwStage = mwRuntimeState?.stage;
                const mwProgress =
                  typeof mwRuntimeState?.progress === "number"
                    ? Math.max(0, Math.min(1, mwRuntimeState.progress))
                    : undefined;
                const mwProgressPercent =
                  typeof mwProgress === "number" ? Math.round(mwProgress * 100) : undefined;
                const mwProgressDisplay =
                  typeof mwProgressPercent === "number"
                    ? Math.max(0, Math.min(100, mwProgressPercent))
                    : undefined;
                const mwStageClass =
                  mwStage && mwStage.length
                    ? mwStage.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")
                    : undefined;
                const mwPackage = formatPackage(mw.node);
                const buildHandleId = (dir: "input" | "output", key: string) =>
                  `mw:${mw.id}:${dir === "input" ? "in" : "out"}:${key}`;
                const hostId = workflowNode?.id ?? nodeId;
                const isDropTarget =
                  draggingMiddlewareId != null && middlewareDragRef.current !== mw.id;
                const onDragStart = (event: DragEvent) => {
                  event.stopPropagation();
                  middlewareDragRef.current = mw.id;
                  setDraggingMiddlewareId(mw.id);
                  event.dataTransfer.effectAllowed = "move";
                  try {
                    event.dataTransfer.setData("application/x-middleware", mw.id);
                  } catch {
                    // ignore when not supported
                  }
                };
                const onDragOver = (event: DragEvent) => {
                  if (!draggingMiddlewareId) {
                    return; // allow external drops (e.g., palette) to bubble to outer handler
                  }
                  event.preventDefault();
                  event.stopPropagation();
                  event.dataTransfer.dropEffect = "move";
                  if (draggingMiddlewareId !== mw.id) {
                    setHoverMiddlewareId(mw.id);
                  }
                };
                const onDrop = (event: DragEvent) => {
                  if (!draggingMiddlewareId) {
                    return; // let outer drop handler attach new middleware
                  }
                  event.preventDefault();
                  event.stopPropagation();
                  const sourceId =
                    middlewareDragRef.current ||
                    event.dataTransfer.getData("application/x-middleware");
                  middlewareDragRef.current = null;
                  setHoverMiddlewareId(null);
                  setDraggingMiddlewareId(null);
                  if (!sourceId || !hostId || sourceId === mw.id) {
                    return;
                  }
                  reorderMiddleware(hostId, sourceId, mw.id);
                };
                const onDragEnd = () => {
                  middlewareDragRef.current = null;
                  setDraggingMiddlewareId(null);
                  setHoverMiddlewareId(null);
                };
                const isDragSource = draggingMiddlewareId === mw.id;
                const showDropSlot =
                  hoverMiddlewareId === mw.id && draggingMiddlewareId != null && draggingMiddlewareId !== mw.id;
                return (
                  <div key={mw.id}>
                    {showDropSlot && <div className="workflow-node__middleware-drop-slot" />}
                    <div
                      className={clsx("workflow-node__middleware-card", "nodrag", {
                        "workflow-node__middleware-card--dragging": isDragSource,
                        "workflow-node__middleware-card--drop-target": isDropTarget,
                      })}
                      role="button"
                      tabIndex={0}
                      draggable
                      onDragStart={onDragStart}
                      onDragOver={onDragOver}
                      onDrop={onDrop}
                      onDragEnd={onDragEnd}
                      onPointerDown={(e) => e.stopPropagation()}
                    >
                      <header className="workflow-node__middleware-card__header">
                        <div className="workflow-node__middleware-card__title">
                          <span className="workflow-node__middleware-index">#{mw.index + 1}</span>
                          <span>{mw.label}</span>
                        </div>
                        <div className="workflow-node__header-badges">
                          {mwStage && (
                            <span
                              className={clsx(
                                "workflow-node__stage",
                                mwStageClass ? `workflow-node__stage--${mwStageClass}` : undefined,
                              )}
                            >
                              {formatStage(mwStage)}
                              {typeof mwProgressDisplay === "number" && (
                                <span className="workflow-node__stage-progress">
                                  (
                                  <span className="workflow-node__stage-progress-value">
                                    {mwProgressDisplay.toString().padStart(3, "\u00a0")}
                                  </span>
                                  %)
                                </span>
                              )}
                            </span>
                          )}
                          {mwStatus && <span className="workflow-node__status">{mwStatus}</span>}
                          <button
                            type="button"
                            className="workflow-node__middleware-remove"
                            onClick={(e) => {
                              e.stopPropagation();
                              removeMiddleware(hostId ?? nodeId, mw.id);
                            }}
                            title="Remove middleware"
                          >
                            ×
                          </button>
                        </div>
                      </header>
                      <div className="workflow-node__middleware-card__body">
                        <div className="workflow-node__badges">
                          <span className="workflow-node__package">{mwPackage}</span>
                        </div>
                        {mwWidgets.length ? (
                          <div
                            className="workflow-node__middleware-widgets workflow-node__widgets nodrag"
                            onPointerDown={(event) => event.stopPropagation()}
                          >
                            {mwWidgets}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
});

WorkflowNode.displayName = "WorkflowNode";

export default WorkflowNode;






