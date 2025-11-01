import { useMemo } from "react";
import type { ReactElement } from "react";
import { useWorkflowStore } from "../store";
import { useWidgetRegistry, registerBuiltinWidgets } from "../widgets";
import { getBindingValue, isBindingEditable, resolveWidgetBinding, setBindingValue } from "../utils/binding";
import type { NodeWidgetDefinition, WorkflowNodeDraft } from "../types";

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
