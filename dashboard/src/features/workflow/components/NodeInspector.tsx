import { useEffect, useMemo, useState } from "react";
import { useWorkflowStore } from "../store";
import { formatBindingDisplay, resolveBindingPath } from "../utils/binding";
import type { NodePortDefinition, WorkflowDraft, WorkflowMiddlewareDraft, WorkflowNodeDraft } from "../types";
import { widgetRegistry, registerBuiltinWidgets } from "../widgets";

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
        mode: changes.mode ?? existing.binding.mode,
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
          mode: kind === "input" ? "write" : "read",
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

  const updateWidgetBinding = (widgetKey: string, nextPrefix: string) => {
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
      if (!existing.binding) {
        return current;
      }
      const nextBinding = {
        ...existing.binding,
        prefix: nextPrefix.trim() ? nextPrefix.trim() : undefined
      };
      widgets[index] = { ...existing, binding: nextBinding };
      return {
        ...current,
        ui: {
          ...ui,
          widgets
        }
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
      const nextBinding = existing.binding
        ? {
            ...existing.binding,
            path: changes.path !== undefined ? changes.path.trim() : existing.binding.path,
            mode: changes.mode ?? existing.binding.mode,
            prefix:
              changes.prefix !== undefined
                ? changes.prefix.trim()
                  ? changes.prefix.trim()
                  : undefined
                : existing.binding.prefix
          }
        : undefined;
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

  const bindingModes = ["read", "write", "two_way"];

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
          mode: "two_way",
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

  return (
    <aside className="inspector">
      <NodeMeta node={node} onLabelChange={updateNodeLabel} />
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










