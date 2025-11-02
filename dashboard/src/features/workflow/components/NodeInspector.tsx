import { useMemo } from "react";
import type { ReactElement } from "react";
import { useWorkflowStore } from "../store";
import { useWidgetRegistry, registerBuiltinWidgets } from "../widgets";
import { getBindingValue, isBindingEditable, resolveWidgetBinding, setBindingValue } from "../utils/binding";
import type { NodePortDefinition, NodeWidgetDefinition, WorkflowNodeDraft } from "../types";

registerBuiltinWidgets();

const NodeMeta = ({ node }: { node: WorkflowNodeDraft }) => (
  <div className="card inspector__summary">
    <header className="card__header">
      <h3>{node.label}</h3>
      <span className="text-subtle">{node.nodeKind}</span>
    </header>
    <dl className="data-grid inspector__meta-grid">
      <div>
        <dt>Package</dt>
        <dd>
          {node.packageName ? `${node.packageName}@${node.packageVersion ?? "latest"}` : "-"}
        </dd>
      </div>
      <div>
        <dt>Adapter</dt>
        <dd>{node.adapter ?? "-"}</dd>
      </div>
      <div>
        <dt>Handler</dt>
        <dd>{node.handler ?? "-"}</dd>
      </div>
      <div>
        <dt>Dependencies</dt>
        <dd>{node.dependencies.length ? node.dependencies.join(", ") : "-"}</dd>
      </div>
      <div>
        <dt>Concurrency Key</dt>
        <dd>{node.concurrencyKey ?? "-"}</dd>
      </div>
    </dl>
  </div>
);

type PortOrigin = "declared" | "inferred";

interface InspectorPort {
  key: string;
  label: string;
  bindingPath?: string | null;
  bindingMode?: string | null;
  origin: PortOrigin;
}

const collectPorts = (
  ports: NodePortDefinition[] | undefined,
  fallbackKeys: Set<string>
): InspectorPort[] => {
  const declared = (ports ?? []).map<InspectorPort>((port) => ({
    key: port.key,
    label: port.label,
    bindingPath: port.binding?.path ?? null,
    bindingMode: port.binding?.mode ?? null,
    origin: "declared"
  }));
  const declaredKeys = new Set(declared.map((port) => port.key));

  fallbackKeys.forEach((key) => {
    if (!declaredKeys.has(key)) {
      declared.push({
        key,
        label: key,
        bindingPath: null,
        bindingMode: null,
        origin: "inferred"
      });
    }
  });

  return declared;
};

interface WidgetEntry {
  widget: NodeWidgetDefinition;
  element: ReactElement;
  key: string;
}

export const NodeInspector = () => {
  const { resolve } = useWidgetRegistry();
  const selectedNodeId = useWorkflowStore((state) => state.selectedNodeId);
  const workflow = useWorkflowStore((state) => state.workflow);
  const updateNode = useWorkflowStore((state) => state.updateNode);

  const node = selectedNodeId ? workflow?.nodes[selectedNodeId] : undefined;

  const ports = useMemo(() => {
    if (!node) {
      return { inputs: [] as InspectorPort[], outputs: [] as InspectorPort[] };
    }

    const fallbackInputs = new Set<string>();
    const fallbackOutputs = new Set<string>();
    workflow?.edges.forEach((edge) => {
      const inputKey = edge.target.portId;
      const outputKey = edge.source.portId;
      if (edge.target.nodeId === node.id && inputKey) {
        fallbackInputs.add(inputKey);
      }
      if (edge.source.nodeId === node.id && outputKey) {
        fallbackOutputs.add(outputKey);
      }
    });

    return {
      inputs: collectPorts(node.ui?.inputPorts, fallbackInputs),
      outputs: collectPorts(node.ui?.outputPorts, fallbackOutputs)
    };
  }, [node, workflow]);

  const widgets = useMemo<WidgetEntry[]>(() => {
    if (!node?.ui?.widgets?.length) {
      return [];
    }
    return node.ui.widgets.reduce<WidgetEntry[]>((accumulator, widget) => {
      const binding = resolveWidgetBinding(widget);
      if (!binding) {
        return accumulator;
      }
      const registration = resolve(widget);
      if (!registration) {
        return accumulator;
      }
      const value = getBindingValue(node, binding);
      const readOnly = !isBindingEditable(widget.binding?.mode) || binding.root === "results";

      const handleChange = (nextValue: unknown) => {
        updateNode(node.id, (current) => setBindingValue(current, binding, nextValue));
      };

      const element = (
        <registration.component
          key={widget.key}
          widget={widget}
          node={node}
          value={value}
          onChange={handleChange}
          readOnly={readOnly}
        />
      );

      accumulator.push({ widget, element, key: widget.key });
      return accumulator;
    }, []);
  }, [node, resolve, updateNode]);

  if (!node) {
    return (
      <div className="card inspector inspector--empty">
        <p>Select a node to edit its parameters.</p>
      </div>
    );
  }

  return (
    <aside className="inspector">
      <NodeMeta node={node} />
      <div className="card inspector__panel">
        <header className="card__header">
          <h3>Ports</h3>
        </header>
        <div className="inspector__ports">
          <div className="inspector__ports-column">
            <h4 className="inspector__ports-heading">Inputs</h4>
            {ports.inputs.length ? (
              <ul className="inspector__port-list">
                {ports.inputs.map((port) => (
                  <li key={`input-${port.key}`} className="inspector__port">
                    <div className="inspector__port-header">
                      <span className="inspector__port-key">{port.key}</span>
                      {port.origin === "inferred" && <span className="badge badge--muted">inferred</span>}
                    </div>
                    <div className="inspector__port-label">{port.label}</div>
                    {port.bindingPath && (
                      <div className="inspector__port-binding">
                        <span>Binding</span>
                        <code className="inspector__port-code">{port.bindingPath}</code>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-subtle">No input ports.</p>
            )}
          </div>
          <div className="inspector__ports-column">
            <h4 className="inspector__ports-heading">Outputs</h4>
            {ports.outputs.length ? (
              <ul className="inspector__port-list">
                {ports.outputs.map((port) => (
                  <li key={`output-${port.key}`} className="inspector__port">
                    <div className="inspector__port-header">
                      <span className="inspector__port-key">{port.key}</span>
                      {port.origin === "inferred" && <span className="badge badge--muted">inferred</span>}
                    </div>
                    <div className="inspector__port-label">{port.label}</div>
                    {port.bindingPath && (
                      <div className="inspector__port-binding">
                        <span>Binding</span>
                        <code className="inspector__port-code">{port.bindingPath}</code>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-subtle">No output ports.</p>
            )}
          </div>
        </div>
      </div>
      <div className="card inspector__panel">
        <header className="card__header">
          <h3>Parameters</h3>
        </header>
        {!widgets.length ? (
          <p className="text-subtle">No editable widgets declared for this node.</p>
        ) : (
          <div className="inspector__widgets">
            {widgets.map((entry) => (
              <div key={entry.key} className="inspector__widget">
                {entry.element}
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
};

export default NodeInspector;
