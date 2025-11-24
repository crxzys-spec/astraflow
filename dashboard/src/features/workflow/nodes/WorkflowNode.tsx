import clsx from "clsx";
import { memo, useEffect, useMemo, useState } from "react";
import type { ReactElement } from "react";
import type { NodeProps } from "reactflow";
import { Handle, Position } from "reactflow";
import type { NodePortDefinition, NodeWidgetDefinition, WorkflowNodeDraft } from "../types.ts";
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
import { UIBindingMode } from "../../../api/models/uIBindingMode";
import { useWidgetRegistry, registerBuiltinWidgets } from "../widgets";

interface WorkflowNodeData {
  nodeId: string;
  label?: string;
  status?: string;
  stage?: string;
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
  const workflowNode = useWorkflowStore((state) => state.workflow?.nodes[nodeId]);
  const workflowEdges = useWorkflowStore((state) => state.workflow?.edges ?? []);
  const updateNode = useWorkflowStore((state) => state.updateNode);
  const { resolve } = useWidgetRegistry();

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
  const inputPorts = mergePorts(workflowNode?.ui?.inputPorts, data?.fallbackInputPorts);
  const outputPorts = mergePorts(workflowNode?.ui?.outputPorts, data?.fallbackOutputPorts);
  const adapter = workflowNode?.adapter ?? data?.adapter;
  const handler = workflowNode?.handler ?? data?.handler;
  const widgets = workflowNode?.ui?.widgets ?? data?.widgets ?? [];
  const [connectedWidgetExpansion, setConnectedWidgetExpansion] = useState<Record<string, boolean>>({});

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
    ...(stageClass ? { [`workflow-node--stage-${stageClass}`]: true } : {}),
  });

  const isContainerNode = workflowNode?.nodeKind === "workflow.container";

  return (
    <div className={nodeClassName}>
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
          {inputPorts.map((port) => {
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
            {(adapter || handler) && (
              <div className="workflow-node__meta">
                {adapter && (
                  <span className="workflow-node__meta-item">
                    <span className="workflow-node__meta-item-label">Adapter</span>
                    <span className="workflow-node__meta-item-value">{adapter}</span>
                  </span>
                )}
                {handler && (
                  <span className="workflow-node__meta-item">
                    <span className="workflow-node__meta-item-label">Handler</span>
                    <span className="workflow-node__meta-item-value">{handler}</span>
                  </span>
                )}
              </div>
            )}
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
          {outputPorts.map((port) => {
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
    </div>
  );
});

WorkflowNode.displayName = "WorkflowNode";

export default WorkflowNode;






