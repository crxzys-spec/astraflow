import { useCallback, useEffect, useMemo, useState } from "react";
import { nanoid } from "nanoid";
import { useWorkflowStore } from "../store";
import { formatBindingDisplay, resolveBindingPath } from "../utils/binding";
import type { NodePortDefinition, WorkflowDraft, WorkflowNodeDraft } from "../types";
import { widgetRegistry, registerBuiltinWidgets } from "../widgets";
import {
  ResourceGrantAction,
  ResourceGrantScope,
  UIBindingModeEnum,
  type ManifestResourceRequirement,
  type PackageDetail,
  type Resource,
  type ResourceGrant,
  type UIBindingModeEnum as UIBindingMode,
} from "../../../client/models";
import { getPackage } from "../../../services/packages";
import { resourcesGateway } from "../../../services/resources";

registerBuiltinWidgets();

const formatPackageId = (node: WorkflowNodeDraft) => {
  if (!node.packageName) {
    return "-";
  }
  return `${node.packageName}@${node.packageVersion ?? "latest"}`;
};

const NodeMeta = ({ node, onLabelChange }: { node: WorkflowNodeDraft; onLabelChange: (value: string) => void }) => {
  const [isEditingLabel, setIsEditingLabel] = useState(false);

  useEffect(() => {
    setIsEditingLabel(false);
  }, [node.id]);

  const stopEditing = () => setIsEditingLabel(false);

  return (
    <div className="card inspector__summary">
      <header className="card__header inspector__summary-header">
        <div className="inspector__summary-title">
          {isEditingLabel ? (
            <input
              className="inspector__summary-title-input"
              type="text"
              value={node.label ?? ""}
              onChange={(event) => onLabelChange(event.target.value)}
              onBlur={stopEditing}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === "Escape") {
                  stopEditing();
                }
              }}
              autoFocus
              aria-label="Node label"
            />
          ) : (
            <button
              type="button"
              className="inspector__summary-title-display"
              onClick={() => setIsEditingLabel(true)}
              aria-label="Edit node label"
              title="Click to edit"
            >
              {node.label || "Untitled node"}
            </button>
          )}
        </div>
        <div className="inspector__summary-meta">
          <span className="inspector__badge">{node.nodeKind}</span>
          <span className="inspector__badge inspector__badge--muted">{formatPackageId(node)}</span>
          <span className="inspector__badge inspector__badge--muted">{node.category ?? "-"}</span>
          <span className="inspector__badge inspector__badge--status">{node.status ?? "-"}</span>
        </div>
      </header>
      <div className="inspector__summary-grid">
        <div className="inspector__field">
          <span className="inspector__field-label">Node ID</span>
          <span className="inspector__field-value inspector__field-value--mono">{node.id}</span>
        </div>
        <div className="inspector__field">
          <span className="inspector__field-label">Tags</span>
          {node.tags && node.tags.length ? (
            <div className="inspector__tags">
              {node.tags.map((tag) => (
                <span key={tag} className="inspector__pill inspector__pill--muted">
                  {tag}
                </span>
              ))}
            </div>
          ) : (
            <span className="inspector__field-value">-</span>
          )}
        </div>
      </div>
    </div>
  );
};

const normalizeGrantActions = (actions?: string[]): ResourceGrantAction[] => {
  const allowed = new Set(Object.values(ResourceGrantAction));
  const normalized = (actions ?? [])
    .map((action) => action?.toString().trim().toLowerCase())
    .filter((action): action is ResourceGrantAction => Boolean(action && allowed.has(action as ResourceGrantAction)));
  return normalized.length ? normalized : [ResourceGrantAction.Read];
};

const formatResourceSize = (size?: number | null): string => {
  if (size == null) {
    return "";
  }
  return `${size.toLocaleString()} bytes`;
};

type PortOrigin = "declared" | "inferred";
type PortKind = "input" | "output";

interface InspectorPort {
  key: string;
  label: string;
  bindingPath?: string | null;
  bindingPrefix?: string | null;
  bindingMode?: string | null;
  origin: PortOrigin;
  kind: PortKind;
}

const collectPorts = (
  ports: NodePortDefinition[] | undefined,
  fallbackKeys: Set<string>,
  kind: PortKind
): InspectorPort[] => {
  const declared = (ports ?? []).map<InspectorPort>((port) => {
    const resolution = resolveBindingPath(port.binding?.path ?? "");
    const bindingPath = formatBindingDisplay(port.binding, resolution);
    return {
      key: port.key,
      label: port.label,
      bindingPath: bindingPath ?? null,
      bindingPrefix: port.binding?.prefix ?? null,
      bindingMode: port.binding?.mode ?? null,
      origin: "declared",
      kind
    };
  });
  const declaredKeys = new Set(declared.map((port) => port.key));

  fallbackKeys.forEach((key) => {
    if (!declaredKeys.has(key)) {
      declared.push({
        key,
        label: key,
        bindingPath: null,
        bindingPrefix: null,
        bindingMode: null,
        origin: "inferred",
        kind
      });
    }
  });

  return declared;
};

export const NodeInspector = () => {
  const selectedNodeId = useWorkflowStore((state) => state.selectedNodeId);
  const rootWorkflow = useWorkflowStore((state) => state.workflow);
  const activeGraph = useWorkflowStore((state) => state.activeGraph);
  const subgraphDrafts = useWorkflowStore((state) => state.subgraphDrafts);
  const updateNode = useWorkflowStore((state) => state.updateNode);
  const setActiveGraph = useWorkflowStore((state) => state.setActiveGraph);
  const inlineSubgraph = useWorkflowStore((state) => state.inlineSubgraphIntoActiveGraph);
  const workflow: WorkflowDraft | undefined = useMemo(() => {
    if (!rootWorkflow) {
      return undefined;
    }
    if (activeGraph.type === "subgraph") {
      const subgraph = subgraphDrafts.find((entry) => entry.id === activeGraph.subgraphId)?.definition;
      return subgraph ?? rootWorkflow;
    }
    return rootWorkflow;
  }, [rootWorkflow, activeGraph, subgraphDrafts]);
  const node = selectedNodeId ? workflow?.nodes[selectedNodeId] : undefined;
  const widgetComponentOptions = useMemo(() => {
    const ids = new Set<string>();
    try {
      widgetRegistry.entries().forEach(([id]) => ids.add(id));
    } catch {
      // ignore
    }
    if (workflow?.nodes) {
      Object.values(workflow.nodes).forEach((draft) => {
        draft.ui?.widgets?.forEach((widget) => {
          if (widget.component) {
            ids.add(widget.component);
          }
        });
      });
    }
    node?.ui?.widgets?.forEach((widget) => {
      if (widget.component) {
        ids.add(widget.component);
      }
    });
    return Array.from(ids);
  }, [workflow?.nodes, node?.ui?.widgets]);

  const [inlineStatus, setInlineStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [packageDetail, setPackageDetail] = useState<PackageDetail | null>(null);
  const [packageLoading, setPackageLoading] = useState(false);
  const [packageError, setPackageError] = useState<string | null>(null);
  const [grants, setGrants] = useState<ResourceGrant[]>([]);
  const [grantLoading, setGrantLoading] = useState(false);
  const [grantError, setGrantError] = useState<string | null>(null);
  const [grantStatus, setGrantStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [grantInputs, setGrantInputs] = useState<Record<string, string>>({});
  const [grantScopes, setGrantScopes] = useState<Record<string, ResourceGrantScope>>({});
  const [grantSecrets, setGrantSecrets] = useState<Record<string, string>>({});
  const [grantSecretNames, setGrantSecretNames] = useState<Record<string, string>>({});
  const [grantSecretProviders, setGrantSecretProviders] = useState<Record<string, string>>({});
  const [resourceOptions, setResourceOptions] = useState<Resource[]>([]);
  const [resourceLoading, setResourceLoading] = useState(false);
  const [resourceError, setResourceError] = useState<string | null>(null);
  const [resourcePickerKey, setResourcePickerKey] = useState<string | null>(null);
  const [resourceSearch, setResourceSearch] = useState("" as string);

  useEffect(() => {
    setInlineStatus(null);
  }, [node?.id]);

  useEffect(() => {
    setGrantStatus(null);
    setGrantError(null);
    setGrantInputs({});
    setGrantScopes({});
    setGrantSecrets({});
    setGrantSecretNames({});
    setGrantSecretProviders({});
  }, [node?.id]);

  useEffect(() => {
    setResourceOptions([]);
    setResourceError(null);
    setResourceSearch("");
    setResourcePickerKey(null);
  }, [node?.id]);

  const requirements = useMemo<ManifestResourceRequirement[]>(() => {
    return packageDetail?.manifest?.requirements?.resources ?? [];
  }, [packageDetail]);

  const workflowId = rootWorkflow?.id;
  const packageName = node?.packageName;
  const packageVersion = packageDetail?.version ?? node?.packageVersion;

  useEffect(() => {
    let isActive = true;
    if (!packageName) {
      setPackageDetail(null);
      setPackageError(null);
      setPackageLoading(false);
      return () => {
        isActive = false;
      };
    }
    setPackageLoading(true);
    setPackageError(null);
    getPackage(packageName, node?.packageVersion)
      .then((detail) => {
        if (!isActive) {
          return;
        }
        setPackageDetail(detail);
      })
      .catch(() => {
        if (!isActive) {
          return;
        }
        setPackageDetail(null);
        setPackageError("Unable to load package requirements.");
      })
      .finally(() => {
        if (!isActive) {
          return;
        }
        setPackageLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, [packageName, node?.packageVersion]);

  const refreshGrants = useCallback(async () => {
    if (!packageName) {
      setGrants([]);
      return;
    }
    setGrantLoading(true);
    setGrantError(null);
    try {
      const requests: Promise<ResourceGrant[]>[] = [
        resourcesGateway.listGrants({
          packageName,
          packageVersion,
          scope: ResourceGrantScope.Global,
        }),
      ];
      if (workflowId) {
        requests.push(
          resourcesGateway.listGrants({
            workflowId,
            packageName,
            packageVersion,
            scope: ResourceGrantScope.Workflow,
          }),
        );
      }
      const results = await Promise.all(requests);
      setGrants(results.flat());
    } catch (error) {
      console.error("Failed to load resource grants", error);
      setGrants([]);
      setGrantError("Unable to load resource grants.");
    } finally {
      setGrantLoading(false);
    }
  }, [packageName, packageVersion, workflowId]);

  useEffect(() => {
    if (!packageName) {
      setGrants([]);
      return;
    }
    refreshGrants();
  }, [packageName, refreshGrants]);

  const loadResources = useCallback(async (searchValue?: string) => {
    setResourceLoading(true);
    setResourceError(null);
    try {
      const items = await resourcesGateway.listResources({
        limit: 20,
        search: searchValue?.trim() ? searchValue.trim() : undefined,
        ownerId: "me",
      });
      setResourceOptions(items);
    } catch (error) {
      console.error("Failed to load resources", error);
      setResourceOptions([]);
      setResourceError("Unable to load resources.");
    } finally {
      setResourceLoading(false);
    }
  }, []);

  const ports = useMemo(() => {
    if (!node) {
      return { inputs: [] as InspectorPort[], outputs: [] as InspectorPort[] };
    }

    const fallbackInputs = new Set<string>();
    const fallbackOutputs = new Set<string>();
    workflow?.edges.forEach((edge) => {
      const inputKey = edge.target.portId;
      const outputKey = edge.source.portId;
      if (edge.target.nodeId === node.id && inputKey && !inputKey.startsWith("mw:")) {
        fallbackInputs.add(inputKey);
      }
      if (edge.source.nodeId === node.id && outputKey && !outputKey.startsWith("mw:")) {
        fallbackOutputs.add(outputKey);
      }
    });

    const middlewareInputPorts =
      node.middlewares?.flatMap((mw) =>
        (mw.ui?.inputPorts ?? []).map((port) => ({
          ...port,
          key: `mw:${mw.id}:input:${port.key}`,
          label: `${mw.label ?? "Middleware"} · ${port.label ?? port.key}`
        }))
      ) ?? [];
    const middlewareOutputPorts =
      node.middlewares?.flatMap((mw) =>
        (mw.ui?.outputPorts ?? []).map((port) => ({
          ...port,
          key: `mw:${mw.id}:output:${port.key}`,
          label: `${mw.label ?? "Middleware"} · ${port.label ?? port.key}`
        }))
      ) ?? [];

    return {
      inputs: collectPorts([...(node.ui?.inputPorts ?? []), ...middlewareInputPorts], fallbackInputs, "input"),
      outputs: collectPorts([...(node.ui?.outputPorts ?? []), ...middlewareOutputPorts], fallbackOutputs, "output")
    };
  }, [node, workflow]);

  function normalizeMode(mode?: string | UIBindingMode | null): UIBindingMode | undefined {
    if (!mode) {
      return undefined;
    }
    const lower = mode.toString().toLowerCase();
    if (lower === "read" || lower === "write" || lower === "two_way") {
      return lower as UIBindingMode;
    }
    return undefined;
  }

  const removeMiddleware = (middlewareId: string) => {
    if (!node) {
      return;
    }
    updateNode(node.id, (current) => ({
      ...current,
      middlewares: (current.middlewares || []).filter((entry) => entry.id !== middlewareId)
    }));
  };

  const moveMiddleware = (middlewareId: string, direction: -1 | 1) => {
    if (!node) {
      return;
    }
    updateNode(node.id, (current) => {
      const list = [...(current.middlewares || [])];
      const index = list.findIndex((item) => item.id === middlewareId);
      if (index === -1) {
        return current;
      }
      const target = index + direction;
      if (target < 0 || target >= list.length) {
        return current;
      }
      const [item] = list.splice(index, 1);
      list.splice(target, 0, item);
      return { ...current, middlewares: list };
    });
  };

  const updatePortBinding = (port: InspectorPort, nextPrefix: string) => {
    if (!node) {
      return;
    }
    updateNode(node.id, (current) => {
      const ui = current.ui ?? {};
      const key = port.kind === "input" ? "inputPorts" : "outputPorts";
      const ports = [...((ui[key] as NodePortDefinition[] | undefined) ?? [])];
      const index = ports.findIndex((candidate) => candidate.key === port.key);
      if (index === -1) {
        return current;
      }
      const existing = ports[index];
      if (!existing.binding) {
        return current;
      }
      const nextBinding = {
        ...existing.binding,
        prefix: nextPrefix.trim() ? nextPrefix.trim() : undefined
      };
      ports[index] = {
        ...existing,
        binding: nextBinding
      };
      return {
        ...current,
        ui: {
          ...ui,
          [key]: ports
        }
      };
    });
  };

  const updatePortBindingFields = (
    port: InspectorPort,
    changes: { path?: string; mode?: string; prefix?: string; label?: string; key?: string }
  ) => {
    if (!node) {
      return;
    }
    updateNode(node.id, (current) => {
      const ui = current.ui ?? {};
      const key = port.kind === "input" ? "inputPorts" : "outputPorts";
      const ports = [...((ui[key] as NodePortDefinition[] | undefined) ?? [])];
      const index = ports.findIndex((candidate) => candidate.key === port.key);
      if (index === -1) {
        return current;
      }
      const existing = ports[index];
      if (!existing.binding) {
        return current;
      }
      const nextBinding = {
        ...existing.binding,
        path: changes.path !== undefined ? changes.path.trim() : existing.binding.path,
        mode: normalizeMode(changes.mode) ?? existing.binding.mode,
        prefix:
          changes.prefix !== undefined
            ? changes.prefix.trim()
              ? changes.prefix.trim()
              : undefined
            : existing.binding.prefix
      };
      const nextKey = changes.key ?? existing.key;
      const nextLabel = changes.label ?? existing.label;
      ports[index] = { ...existing, key: nextKey, label: nextLabel, binding: nextBinding };
      return {
        ...current,
        ui: {
          ...ui,
          [key]: ports
        }
      };
    });
  };

  const addPort = (kind: PortKind) => {
    if (!node) {
      return;
    }
    updateNode(node.id, (current) => {
      const ui = current.ui ?? {};
      const key = kind === "input" ? "inputPorts" : "outputPorts";
      const ports = [...((ui[key] as NodePortDefinition[] | undefined) ?? [])];
      const index = ports.length + 1;
      const newPort: NodePortDefinition = {
        key: `${kind}-${nanoid(5)}`,
        label: `${kind === "input" ? "Input" : "Output"} ${index}`,
        binding: {
          path: kind === "input" ? "/parameters/" : "/results/",
          mode: kind === "input" ? UIBindingModeEnum.Write : UIBindingModeEnum.Read,
        },
      };
      ports.push(newPort);
      return {
        ...current,
        ui: {
          ...ui,
          [key]: ports,
        },
      };
    });
  };

  const removePort = (kind: PortKind, portKey: string) => {
    if (!node) {
      return;
    }
    updateNode(node.id, (current) => {
      const ui = current.ui ?? {};
      const key = kind === "input" ? "inputPorts" : "outputPorts";
      const ports = [...((ui[key] as NodePortDefinition[] | undefined) ?? [])].filter(
        (port) => port.key !== portKey,
      );
      return {
        ...current,
        ui: {
          ...ui,
          [key]: ports,
        },
      };
    });
  };

  const updateWidgetFields = (
    widgetKey: string,
    changes: { path?: string; mode?: string; prefix?: string; component?: string; label?: string; key?: string }
  ) => {
    if (!node) {
      return;
    }
    updateNode(node.id, (current) => {
      const ui = current.ui ?? {};
      const widgets = [...(ui.widgets ?? [])];
      const index = widgets.findIndex((entry) => entry.key === widgetKey);
      if (index === -1) {
        return current;
      }
      const existing = widgets[index];
      const baseBinding = existing.binding ?? {
        path: "",
        mode: UIBindingModeEnum.Read,
        prefix: undefined,
      };
      const nextBinding = {
        ...baseBinding,
        path: changes.path !== undefined ? changes.path.trim() : baseBinding.path,
        mode: normalizeMode(changes.mode) ?? baseBinding.mode,
        prefix:
          changes.prefix !== undefined
            ? changes.prefix.trim()
              ? changes.prefix.trim()
              : undefined
            : baseBinding.prefix
      };
      widgets[index] = {
        ...existing,
        key: changes.key ?? existing.key,
        label: changes.label !== undefined ? changes.label : existing.label,
        component: changes.component !== undefined ? changes.component.trim() : existing.component,
        binding: nextBinding
      };
      return {
        ...current,
        ui: {
          ...ui,
          widgets
        }
      };
    });
  };

  const bindingModes: UIBindingMode[] = [
    UIBindingModeEnum.Read,
    UIBindingModeEnum.Write,
    UIBindingModeEnum.TwoWay,
  ];

  const addWidget = () => {
    if (!node) {
      return;
    }
    updateNode(node.id, (current) => {
      const ui = current.ui ?? {};
      const widgets = [...(ui.widgets ?? [])];
      const newWidget = {
        key: `widget-${nanoid(5)}`,
        label: `Widget ${widgets.length + 1}`,
        component: "text",
        binding: {
          path: "/parameters/",
          mode: UIBindingModeEnum.TwoWay,
        },
      };
      widgets.push(newWidget);
      return {
        ...current,
        ui: {
          ...ui,
          widgets,
        },
      };
    });
  };

  const removeWidget = (widgetKey: string) => {
    if (!node) {
      return;
    }
    updateNode(node.id, (current) => {
      const ui = current.ui ?? {};
      const widgets = [...(ui.widgets ?? [])].filter((entry) => entry.key !== widgetKey);
      return {
        ...current,
        ui: {
          ...ui,
          widgets,
        },
      };
    });
  };

  const containerConfig = useMemo(() => {
    if (!node || node.nodeKind !== "workflow.container") {
      return undefined;
    }
    const raw = node.parameters?.__container as { subgraphId?: unknown } | undefined;
    if (!raw || typeof raw !== "object") {
      return undefined;
    }
    const subgraphId = typeof raw.subgraphId === "string" ? raw.subgraphId : undefined;
    return {
      subgraphId,
    };
  }, [node]);

  const containerSubgraphTarget = useMemo(() => {
    if (!containerConfig?.subgraphId) {
      return undefined;
    }
    return subgraphDrafts.find((entry) => entry.id === containerConfig.subgraphId);
  }, [containerConfig?.subgraphId, subgraphDrafts]);

  const handleInlineSubgraph = () => {
    if (!node) {
      return;
    }
    const runInline = () => {
      const result = inlineSubgraph(node.id);
      if (result.ok) {
        setInlineStatus({ type: "success", message: "Subgraph nodes have been copied into this graph and the container was removed." });
      } else {
        setInlineStatus({ type: "error", message: result.error ?? "Unable to inline the subgraph." });
      }
    };
    if (activeGraph.type === "subgraph") {
      // Always operate from the root workflow view to avoid view/state churn when dissolving.
      setActiveGraph({ type: "root" }, { recordHistory: false });
      setTimeout(runInline, 0);
      return;
    }
    runInline();
  };

  if (!node) {
    return (
      <div className="card inspector inspector--empty">
        <p>Select a node to edit its parameters.</p>
      </div>
    );
  }

  const updateNodeLabel = (nextLabel: string) => {
    if (!node) {
      return;
    }
    updateNode(node.id, (current) => ({
      ...current,
      label: nextLabel
    }));
  };

  const resultData = node.results ?? {};
  const hasResultData = Object.keys(resultData).length > 0;
  const requirementsReady = requirements.length > 0;
  const requirementsBlocked = Boolean(packageError) || (!packageName && !packageLoading);

  return (
    <aside className="inspector">
      <NodeMeta node={node} onLabelChange={updateNodeLabel} />
      {node.nodeKind === "workflow.container" && (
        <div className="card inspector__panel">
          <header className="card__header">
            <h3>Container</h3>
          </header>
          <div className="inspector__section">
            <p className="text-subtle">
              Inline the referenced subgraph into this graph to replace the container node with the actual nodes. A new copy will
              appear near the container&apos;s position so you can wire it manually.
            </p>
            {containerSubgraphTarget && (
              <p className="text-subtle">
                Target: <strong>{containerSubgraphTarget.definition.metadata?.name ?? containerSubgraphTarget.definition.id}</strong>
              </p>
            )}
            {inlineStatus && (
              <p className={inlineStatus.type === "error" ? "error" : "text-subtle"}>
                {inlineStatus.message}
              </p>
            )}
            <button
              type="button"
              className="btn btn--ghost"
              onClick={handleInlineSubgraph}
              disabled={!containerConfig?.subgraphId}
            >
              Inline subgraph into current graph
            </button>
          </div>
        </div>
      )}
      <div className="card inspector__panel">
        <header className="card__header">
          <h3>UI</h3>
        </header>
        <div className="inspector__ports">
          <div className="inspector__ports-column">
            <div className="inspector__ports-heading-row">
              <h4 className="inspector__ports-heading">Input Ports</h4>
              <button type="button" className="inspector__add-btn" onClick={() => addPort("input")}>
                + Add
              </button>
            </div>
            {ports.inputs.length ? (
              <ul className="inspector__port-list">
                {ports.inputs.map((port) => (
                  <li key={`input-${port.key}`} className="inspector__port">
                    <div className="inspector__port-header">
                      <div className="inspector__port-header-row">
                        <span className="inspector__port-label">{port.label}</span>
                        {port.origin === "inferred" && <span className="badge badge--muted">inferred</span>}
                      </div>
                      <div className="inspector__port-actions">
                        <button
                          type="button"
                          className="inspector__remove-btn"
                          onClick={() => removePort("input", port.key)}
                          aria-label="Remove input port"
                        >
                          &times;
                        </button>
                      </div>
                    </div>
                    <div className="inspector__port-title">
                      <label className="inspector__inline-input">
                        <span>Label</span>
                        <input
                          className="inspector__port-input"
                          type="text"
                          value={port.label}
                          onChange={(event) => updatePortBindingFields(port, { label: event.target.value })}
                        />
                      </label>
                      <label className="inspector__inline-input">
                        <span>Key</span>
                        <input
                          className="inspector__port-input"
                          type="text"
                          value={port.key}
                          onChange={(event) => updatePortBindingFields(port, { key: event.target.value })}
                        />
                      </label>
                    </div>
                    {port.bindingPath && (
                      <>
                        <div className="inspector__port-binding">
                          <span className="inspector__port-binding-label">Binding</span>
                      <input
                        className="inspector__port-input"
                        type="text"
                        value={port.bindingPath ?? ""}
                        onChange={(event) => updatePortBindingFields(port, { path: event.target.value })}
                      />
                    </div>
                    {port.origin === "declared" ? (
                      <label className="inspector__binding-input">
                        <span>Binding prefix</span>
                        <input
                          type="text"
                          value={port.bindingPrefix ?? ""}
                          placeholder="@subgraphAlias.#nodeId"
                          onChange={(event) => updatePortBinding(port, event.target.value)}
                        />
                      </label>
                    ) : (
                      <div className="inspector__port-binding">
                        <span className="inspector__port-binding-label">Binding prefix</span>
                        <code className="inspector__port-code">{port.bindingPrefix ?? "-"}</code>
                      </div>
                    )}
                    {port.bindingMode && (
                      <div className="inspector__port-mode">
                        Mode
                        <select
                          className="inspector__port-select"
                          value={port.bindingMode}
                          onChange={(event) => updatePortBindingFields(port, { mode: event.target.value })}
                        >
                          {bindingModes.map((mode) => (
                            <option key={mode} value={mode}>
                              {mode.toUpperCase()}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </>
                )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-subtle">No input ports.</p>
            )}
          </div>
          <div className="inspector__ports-column">
            <div className="inspector__ports-heading-row">
              <h4 className="inspector__ports-heading">Output Ports</h4>
              <button type="button" className="inspector__add-btn" onClick={() => addPort("output")}>
                + Add
              </button>
            </div>
            {ports.outputs.length ? (
              <ul className="inspector__port-list">
                {ports.outputs.map((port) => (
                  <li key={`output-${port.key}`} className="inspector__port">
                    <div className="inspector__port-header">
                      <div className="inspector__port-header-row">
                        <span className="inspector__port-label">{port.label}</span>
                        {port.origin === "inferred" && <span className="badge badge--muted">inferred</span>}
                      </div>
                      <div className="inspector__port-actions">
                        <button
                          type="button"
                          className="inspector__remove-btn"
                          onClick={() => removePort("output", port.key)}
                          aria-label="Remove output port"
                        >
                          &times;
                        </button>
                      </div>
                    </div>
                    <div className="inspector__port-title">
                      <label className="inspector__inline-input">
                        <span>Label</span>
                        <input
                          className="inspector__port-input"
                          type="text"
                          value={port.label}
                          onChange={(event) => updatePortBindingFields(port, { label: event.target.value })}
                        />
                      </label>
                      <label className="inspector__inline-input">
                        <span>Key</span>
                        <input
                          className="inspector__port-input"
                          type="text"
                          value={port.key}
                          onChange={(event) => updatePortBindingFields(port, { key: event.target.value })}
                        />
                      </label>
                    </div>
                    {port.bindingPath && (
                      <>
                    <div className="inspector__port-binding">
                      <span className="inspector__port-binding-label">Binding</span>
                      <input
                        className="inspector__port-input"
                        type="text"
                        value={port.bindingPath ?? ""}
                        onChange={(event) => updatePortBindingFields(port, { path: event.target.value })}
                      />
                    </div>
                    {port.origin === "declared" ? (
                      <label className="inspector__binding-input">
                        <span>Binding prefix</span>
                        <input
                          type="text"
                          value={port.bindingPrefix ?? ""}
                          placeholder="@subgraphAlias.#nodeId"
                          onChange={(event) => updatePortBinding(port, event.target.value)}
                        />
                      </label>
                    ) : (
                      <div className="inspector__port-binding">
                        <span className="inspector__port-binding-label">Binding prefix</span>
                        <code className="inspector__port-code">{port.bindingPrefix ?? "-"}</code>
                      </div>
                    )}
                    {port.bindingMode && (
                      <div className="inspector__port-mode">
                        Mode
                        <select
                          className="inspector__port-select"
                          value={port.bindingMode}
                          onChange={(event) => updatePortBindingFields(port, { mode: event.target.value })}
                        >
                          {bindingModes.map((mode) => (
                            <option key={mode} value={mode}>
                              {mode.toUpperCase()}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </>
                )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-subtle">No output ports.</p>
            )}
          </div>
        </div>
        <div className="inspector__widgets">
          <div className="inspector__ports-heading-row">
            <h4 className="inspector__ports-heading">Widgets</h4>
            <button type="button" className="inspector__add-btn" onClick={addWidget}>
              + Add
            </button>
          </div>
          {node.ui?.widgets?.length ? (
            <ul className="inspector__widget-list">
              {node.ui.widgets.map((widget) => {
                const resolution = resolveBindingPath(widget.binding?.path ?? "");
                const bindingPath = formatBindingDisplay(widget.binding, resolution);
                return (
                  <li key={widget.key} className="inspector__widget">
                    <div className="inspector__widget-header">
                      <div className="inspector__port-header-row">
                        <span className="inspector__port-label">{widget.label ?? widget.key}</span>
                      </div>
                      <div className="inspector__port-actions">
                        <button
                          type="button"
                          className="inspector__remove-btn"
                          onClick={() => removeWidget(widget.key)}
                          aria-label="Remove widget"
                        >
                          &times;
                        </button>
                      </div>
                    </div>
                    <div className="inspector__port-title">
                      <label className="inspector__inline-input">
                        <span>Label</span>
                        <input
                          className="inspector__port-input"
                          type="text"
                          value={widget.label ?? ""}
                          onChange={(event) =>
                            updateWidgetFields(widget.key, { label: event.target.value || undefined })
                          }
                        />
                      </label>
                      <label className="inspector__inline-input">
                        <span>Key</span>
                        <input
                          className="inspector__port-input"
                          type="text"
                          value={widget.key}
                          onChange={(event) =>
                            updateWidgetFields(widget.key, { key: event.target.value || widget.key })
                          }
                        />
                      </label>
                    </div>
                    {bindingPath && (
                      <div className="inspector__widget-binding">
                        <span className="inspector__widget-binding-label">Binding</span>
                        <input
                          className="inspector__port-input"
                          type="text"
                          value={bindingPath ?? ""}
                          onChange={(event) => updateWidgetFields(widget.key, { path: event.target.value })}
                        />
                      </div>
                    )}
                    <label className="inspector__binding-input">
                      <span>Binding prefix</span>
                      <input
                        type="text"
                        value={widget.binding?.prefix ?? ""}
                        placeholder="@subgraphAlias.#nodeId"
                        onChange={(event) => updateWidgetFields(widget.key, { prefix: event.target.value })}
                      />
                    </label>
                    <div className="inspector__widget-binding">
                      <span className="inspector__widget-binding-label">Component</span>
                      <select
                        className="inspector__port-select"
                        value={widget.component}
                        onChange={(event) => updateWidgetFields(widget.key, { component: event.target.value })}
                      >
                        {Array.from(
                          new Set([
                            ...widgetComponentOptions,
                            widget.component
                          ].filter(Boolean) as string[])
                        ).map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                    {widget.binding?.mode && (
                      <div className="inspector__port-mode">
                        Mode
                        <select
                          className="inspector__port-select"
                          value={widget.binding.mode}
                          onChange={(event) => updateWidgetFields(widget.key, { mode: event.target.value })}
                        >
                          {bindingModes.map((mode) => (
                            <option key={mode} value={mode}>
                              {mode.toUpperCase()}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-subtle inspector__payload-empty">No widgets defined.</p>
          )}
        </div>
      </div>
      {(requirementsReady || packageLoading || packageError) && (
        <div className="card inspector__panel">
          <header className="card__header">
            <h3>Resource Requirements</h3>
          </header>
          <div className="inspector__section">
            {packageLoading && <p className="text-subtle inspector__payload-empty">Loading requirements...</p>}
            {packageError && <p className="error">{packageError}</p>}
            {!packageLoading && !packageError && !requirementsReady && requirementsBlocked && (
              <p className="text-subtle inspector__payload-empty">No resource requirements declared.</p>
            )}
            {grantError && <p className="error">{grantError}</p>}
            {grantStatus && (
              <p className={grantStatus.type === "error" ? "error" : "text-subtle"}>{grantStatus.message}</p>
            )}
            {requirementsReady && (
              <div className="inspector__requirements">
                {requirements.map((requirement) => {
                  const requirementActions = normalizeGrantActions(requirement.actions);
                  const requirementRequired = requirement.required !== false;
                  const scopeValue = grantScopes[requirement.key] ?? ResourceGrantScope.Workflow;
                  const inputValue = grantInputs[requirement.key] ?? "";
                  const isSecret = requirement.type?.toLowerCase() === "secret";
                  const secretValue = grantSecrets[requirement.key] ?? "";
                  const secretName = grantSecretNames[requirement.key] ?? "";
                  const rawSecretProviders = Array.isArray(requirement.metadata?.providers)
                    ? requirement.metadata?.providers
                    : [];
                  const normalizedSecretProviders = rawSecretProviders
                    .map((entry) => entry.toString().trim())
                    .filter((entry) => entry.length > 0);
                  const secretDefaultProvider =
                    (typeof requirement.metadata?.provider === "string"
                      ? requirement.metadata?.provider.trim()
                      : "") ||
                    normalizedSecretProviders[0] ||
                    "local";
                  const secretProviders = normalizedSecretProviders.length
                    ? normalizedSecretProviders
                    : [secretDefaultProvider];
                  const secretProviderLabel =
                    typeof requirement.metadata?.providerLabel === "string"
                      ? requirement.metadata?.providerLabel
                      : "Storage";
                  const secretProvider =
                    grantSecretProviders[requirement.key] ?? secretDefaultProvider;
                  const grantsForKey = grants.filter((grant) => grant.resourceKey === requirement.key);
                  const isPickerOpen = resourcePickerKey === requirement.key;
                  const canGrant =
                    Boolean(inputValue.trim()) &&
                    !grantLoading &&
                    (scopeValue !== ResourceGrantScope.Workflow || Boolean(workflowId));
                  const canCreateSecretGrant =
                    isSecret &&
                    Boolean(secretValue.trim()) &&
                    !grantLoading &&
                    (scopeValue !== ResourceGrantScope.Workflow || Boolean(workflowId));

                  const handleGrant = async () => {
                    if (!packageName || !inputValue.trim()) {
                      return;
                    }
                    if (scopeValue === ResourceGrantScope.Workflow && !workflowId) {
                      setGrantStatus({ type: "error", message: "Workflow ID is required for workflow grants." });
                      return;
                    }
                    setGrantLoading(true);
                    setGrantStatus(null);
                    try {
                      await resourcesGateway.createGrant({
                        resourceId: inputValue.trim(),
                        packageName,
                        packageVersion: packageVersion ?? undefined,
                        resourceKey: requirement.key,
                        scope: scopeValue,
                        workflowId: scopeValue === ResourceGrantScope.Workflow ? workflowId : undefined,
                        actions: requirementActions,
                      });
                      setGrantInputs((prev) => ({ ...prev, [requirement.key]: "" }));
                      await refreshGrants();
                      setGrantStatus({ type: "success", message: "Grant created." });
                    } catch (error) {
                      console.error("Failed to create resource grant", error);
                      setGrantStatus({ type: "error", message: "Failed to create grant." });
                    } finally {
                      setGrantLoading(false);
                    }
                  };

                  const handleRevoke = async (grantId: string) => {
                    setGrantLoading(true);
                    setGrantStatus(null);
                    try {
                      await resourcesGateway.deleteGrant(grantId);
                      await refreshGrants();
                      setGrantStatus({ type: "success", message: "Grant revoked." });
                    } catch (error) {
                      console.error("Failed to revoke resource grant", error);
                      setGrantStatus({ type: "error", message: "Failed to revoke grant." });
                    } finally {
                      setGrantLoading(false);
                    }
                  };

                  const handleCreateSecretGrant = async () => {
                    if (!packageName) {
                      return;
                    }
                    if (scopeValue === ResourceGrantScope.Workflow && !workflowId) {
                      setGrantStatus({ type: "error", message: "Workflow ID is required for workflow grants." });
                      return;
                    }
                    const trimmedSecret = secretValue.trim();
                    if (!trimmedSecret) {
                      return;
                    }
                    setGrantLoading(true);
                    setGrantStatus(null);
                    try {
                      const baseName = secretName.trim() || requirement.key || "secret";
                      const filename = baseName.endsWith(".txt") ? baseName : `${baseName}.txt`;
                      const file = new File([trimmedSecret], filename, { type: "text/plain" });
                      const resource = await resourcesGateway.upload(file, {
                        provider: secretProvider,
                      });
                      await resourcesGateway.createGrant({
                        resourceId: resource.resourceId,
                        packageName,
                        packageVersion: packageVersion ?? undefined,
                        resourceKey: requirement.key,
                        scope: scopeValue,
                        workflowId: scopeValue === ResourceGrantScope.Workflow ? workflowId : undefined,
                        actions: requirementActions,
                      });
                      setGrantInputs((prev) => ({ ...prev, [requirement.key]: resource.resourceId }));
                      setGrantSecrets((prev) => ({ ...prev, [requirement.key]: "" }));
                      setGrantSecretNames((prev) => ({ ...prev, [requirement.key]: "" }));
                      await refreshGrants();
                      if (resourcePickerKey === requirement.key) {
                        await loadResources(resourceSearch);
                      }
                      setGrantStatus({ type: "success", message: "Secret uploaded and granted." });
                    } catch (error) {
                      console.error("Failed to upload secret for grant", error);
                      setGrantStatus({ type: "error", message: "Failed to upload secret." });
                    } finally {
                      setGrantLoading(false);
                    }
                  };

                  return (
                    <div key={requirement.key} className="inspector__requirement">
                      <div className="inspector__requirement-header">
                        <div className="inspector__requirement-title">
                          <span className="inspector__pill inspector__pill--solid">{requirement.key}</span>
                          <span className="inspector__pill inspector__pill--muted">{requirement.type}</span>
                        </div>
                        <span
                          className={`inspector__badge ${requirementRequired ? "inspector__badge--status" : "inspector__badge--muted"}`}
                        >
                          {requirementRequired ? "Required" : "Optional"}
                        </span>
                      </div>
                      {requirement.description && (
                        <p className="inspector__requirement-description">{requirement.description}</p>
                      )}
                      <div className="inspector__requirement-meta">
                        <span className="inspector__field-label">Actions</span>
                        <span className="inspector__field-value">
                          {requirementActions.join(", ")}
                        </span>
                      </div>
                      <div className="inspector__grant-list">
                        {grantLoading && grantsForKey.length === 0 && (
                          <p className="text-subtle inspector__payload-empty">Loading grants...</p>
                        )}
                        {grantsForKey.length ? (
                          grantsForKey.map((grant) => (
                            <div key={grant.grantId} className="inspector__grant-item">
                              <div className="inspector__grant-item-meta">
                                <span className="inspector__pill inspector__pill--muted">
                                  {grant.scope}
                                </span>
                                <span className="inspector__field-value inspector__field-value--mono">
                                  {grant.resourceId}
                                </span>
                                <span className="inspector__pill">
                                  {(grant.actions ?? []).join(", ")}
                                </span>
                              </div>
                              <button
                                type="button"
                                className="btn btn--ghost inspector__grant-button"
                                onClick={() => handleRevoke(grant.grantId)}
                                disabled={grantLoading}
                              >
                                Revoke
                              </button>
                            </div>
                          ))
                        ) : (
                          <p className="text-subtle inspector__payload-empty">No grants yet.</p>
                        )}
                      </div>
                      <div className="inspector__grant-form">
                        <label className="inspector__inline-input">
                          <span>Resource ID</span>
                          <input
                            className="inspector__port-input"
                            type="text"
                            value={inputValue}
                            placeholder="resource_id"
                            onChange={(event) =>
                              setGrantInputs((prev) => ({
                                ...prev,
                                [requirement.key]: event.target.value,
                              }))
                            }
                          />
                        </label>
                        {isSecret && (
                          <div className="inspector__resource-picker">
                            <label className="inspector__inline-input">
                              <span>Secret value</span>
                              <input
                                className="inspector__port-input"
                                type="password"
                                value={secretValue}
                                placeholder="Paste API key"
                                onChange={(event) =>
                                  setGrantSecrets((prev) => ({
                                    ...prev,
                                    [requirement.key]: event.target.value,
                                  }))
                                }
                              />
                            </label>
                            <label className="inspector__inline-input">
                              <span>Resource name</span>
                              <input
                                className="inspector__port-input"
                                type="text"
                                value={secretName}
                                placeholder={`${requirement.key}.txt`}
                                onChange={(event) =>
                                  setGrantSecretNames((prev) => ({
                                    ...prev,
                                    [requirement.key]: event.target.value,
                                  }))
                                }
                              />
                            </label>
                            <label className="inspector__inline-input">
                              <span>{secretProviderLabel}</span>
                              <select
                                className="inspector__port-select"
                                value={secretProvider}
                                onChange={(event) =>
                                  setGrantSecretProviders((prev) => ({
                                    ...prev,
                                    [requirement.key]: event.target.value,
                                  }))
                                }
                              >
                                {secretProviders.map((provider) => (
                                  <option key={provider} value={provider}>
                                    {provider}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <div className="inspector__grant-actions">
                              <button
                                type="button"
                                className="btn btn--ghost inspector__grant-button"
                                onClick={handleCreateSecretGrant}
                                disabled={!canCreateSecretGrant}
                              >
                                Upload &amp; grant
                              </button>
                            </div>
                          </div>
                        )}
                        <div className="inspector__grant-browse">
                          <button
                            type="button"
                            className="btn btn--ghost inspector__grant-button"
                            onClick={() => {
                              if (isPickerOpen) {
                                setResourcePickerKey(null);
                                return;
                              }
                              setResourcePickerKey(requirement.key);
                              if (!resourceOptions.length) {
                                loadResources(resourceSearch);
                              }
                            }}
                          >
                            {isPickerOpen ? "Hide resources" : "Browse resources"}
                          </button>
                          <button
                            type="button"
                            className="btn btn--ghost inspector__grant-button"
                            onClick={() => loadResources(resourceSearch)}
                            disabled={resourceLoading}
                          >
                            Refresh
                          </button>
                        </div>
                        {isPickerOpen && (
                          <div className="inspector__resource-picker">
                            <label className="inspector__inline-input">
                              <span>Search</span>
                              <input
                                className="inspector__port-input"
                                type="text"
                                value={resourceSearch}
                                placeholder="filename or id"
                                onChange={(event) => setResourceSearch(event.target.value)}
                              />
                            </label>
                            <div className="inspector__grant-browse">
                              <button
                                type="button"
                                className="btn btn--ghost inspector__grant-button"
                                onClick={() => loadResources(resourceSearch)}
                                disabled={resourceLoading}
                              >
                                Search
                              </button>
                            </div>
                            {resourceError && <p className="error">{resourceError}</p>}
                            {resourceLoading && (
                              <p className="text-subtle inspector__payload-empty">Loading resources...</p>
                            )}
                            {!resourceLoading && resourceOptions.length === 0 && (
                              <p className="text-subtle inspector__payload-empty">No resources found.</p>
                            )}
                            {!resourceLoading && resourceOptions.length > 0 && (
                              <div className="inspector__resource-list">
                                {resourceOptions.map((resource) => (
                                  <div key={resource.resourceId} className="inspector__resource-item">
                                    <div className="inspector__resource-meta">
                                      <span className="inspector__pill inspector__pill--muted">
                                        {resource.filename || resource.resourceId}
                                      </span>
                                      <span className="inspector__field-value inspector__field-value--mono">
                                        {resource.resourceId}
                                      </span>
                                      {resource.sizeBytes != null && (
                                        <span className="inspector__pill">
                                          {formatResourceSize(resource.sizeBytes)}
                                        </span>
                                      )}
                                    </div>
                                    <button
                                      type="button"
                                      className="btn btn--ghost inspector__grant-button"
                                      onClick={() => {
                                        setGrantInputs((prev) => ({
                                          ...prev,
                                          [requirement.key]: resource.resourceId,
                                        }));
                                        setResourcePickerKey(null);
                                      }}
                                    >
                                      Use
                                    </button>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                        <label className="inspector__inline-input">
                          <span>Scope</span>
                          <select
                            className="inspector__port-select"
                            value={scopeValue}
                            onChange={(event) =>
                              setGrantScopes((prev) => ({
                                ...prev,
                                [requirement.key]: event.target.value as ResourceGrantScope,
                              }))
                            }
                          >
                            <option value={ResourceGrantScope.Workflow}>Workflow</option>
                            <option value={ResourceGrantScope.Global}>Global</option>
                          </select>
                        </label>
                        {scopeValue === ResourceGrantScope.Workflow && (
                          <div className="inspector__field-value inspector__field-value--mono">
                            Workflow: {workflowId ?? "-"}
                          </div>
                        )}
                      </div>
                      <div className="inspector__grant-actions">
                        <button
                          type="button"
                          className="btn btn--ghost inspector__grant-button"
                          onClick={handleGrant}
                          disabled={!canGrant}
                        >
                          Grant access
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
      <div className="card inspector__panel">
        <header className="card__header">
          <h3>Middlewares</h3>
        </header>
        {node?.role === "middleware" ? (
          <p className="text-subtle inspector__payload-empty">
            Middleware nodes cannot attach other middlewares.
          </p>
        ) : (
          <div className="inspector__section">
            {node?.middlewares && node.middlewares.length ? (
              <ul className="inspector__middleware-list">
                {node.middlewares.map((middleware, idx) => {
                  const label = middleware.label || middleware.id;
                  return (
                    <li key={middleware.id} className="inspector__middleware-item">
                      <div className="inspector__middleware-meta">
                        <span className="inspector__pill inspector__pill--solid">#{idx + 1}</span>
                        <span className="inspector__pill">{label}</span>
                        <span className="inspector__field-value inspector__field-value--mono">
                          {middleware.id}
                        </span>
                      </div>
                      <div className="inspector__middleware-actions">
                        <button
                          type="button"
                          className="inspector__icon-button"
                          onClick={() => moveMiddleware(middleware.id, -1)}
                          title="Move up"
                          aria-label="Move middleware up"
                          disabled={idx === 0}
                        >
                          ▲
                        </button>
                        <button
                          type="button"
                          className="inspector__icon-button"
                          onClick={() => moveMiddleware(middleware.id, 1)}
                          title="Move down"
                          aria-label="Move middleware down"
                          disabled={idx === node.middlewares!.length - 1}
                        >
                          ▼
                        </button>
                        <button
                          type="button"
                          className="inspector__icon-button inspector__icon-button--danger"
                          onClick={() => removeMiddleware(middleware.id)}
                          title="Remove middleware"
                          aria-label="Remove middleware"
                        >
                          ✕
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-subtle inspector__payload-empty">No middlewares attached.</p>
            )}
            <p className="text-subtle inspector__payload-hint">
              Drag middleware from the palette onto this node to attach it.
            </p>
          </div>
        )}
      </div>
      <div className="card inspector__panel">
        <header className="card__header">
          <h3>Parameters & Results</h3>
        </header>
        <div className="inspector__stats">
          <section className="inspector__section">
            <h4>Parameters</h4>
            {Object.keys(node.parameters ?? {}).length ? (
              <pre className="inspector__payload inspector__payload--compact">
                {JSON.stringify(node.parameters, null, 2)}
              </pre>
            ) : (
              <p className="text-subtle inspector__payload-empty">No parameters defined.</p>
            )}
          </section>
          <section className="inspector__section">
            <h4>Results</h4>
            {hasResultData ? (
              <pre className="inspector__payload inspector__payload--compact">
                {JSON.stringify(resultData, null, 2)}
              </pre>
            ) : (
              <p className="text-subtle inspector__payload-empty">No results available.</p>
            )}
          </section>
        </div>
      </div>
    </aside>
  );
};

export default NodeInspector;









