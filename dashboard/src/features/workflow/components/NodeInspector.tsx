import { useMemo } from "react";
import { useWorkflowStore } from "../store";
import type { NodePortDefinition, WorkflowNodeDraft } from "../types";

const formatPackageId = (node: WorkflowNodeDraft) => {
  if (!node.packageName) {
    return "-";
  }
  return `${node.packageName}@${node.packageVersion ?? "latest"}`;
};

const formatTags = (tags: string[] | undefined) => {
  if (!tags || tags.length === 0) {
    return "-";
  }
  return tags.join(", ");
};

const NodeMeta = ({ node }: { node: WorkflowNodeDraft }) => (
  <div className="card inspector__summary">
    <header className="card__header">
      <h3>{node.label}</h3>
      <span className="text-subtle">{node.nodeKind}</span>
    </header>
    <dl className="data-grid inspector__meta-grid">
      <div>
        <dt>Node ID</dt>
        <dd>{node.id}</dd>
      </div>
      <div>
        <dt>Package</dt>
        <dd>{formatPackageId(node)}</dd>
      </div>
      <div>
        <dt>Category</dt>
        <dd>{node.category ?? "-"}</dd>
      </div>
      <div>
        <dt>Status</dt>
        <dd>{node.status ?? "-"}</dd>
      </div>
      <div>
        <dt>Tags</dt>
        <dd>{formatTags(node.tags)}</dd>
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

export const NodeInspector = () => {
  const selectedNodeId = useWorkflowStore((state) => state.selectedNodeId);
  const workflow = useWorkflowStore((state) => state.workflow);

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

  if (!node) {
    return (
      <div className="card inspector inspector--empty">
        <p>Select a node to edit its parameters.</p>
      </div>
    );
  }

  const runtimeState = node.state ?? null;
  const runtimeStage = runtimeState?.stage ?? "-";
  const runtimeProgress =
    typeof runtimeState?.progress === "number"
      ? Math.max(0, Math.min(1, runtimeState.progress))
      : undefined;
  const runtimeMessage = runtimeState?.message ?? null;
  const runtimeUpdatedAt = runtimeState?.lastUpdatedAt ?? null;
  const runtimeError = runtimeState?.error;
  const resultData = node.results ?? {};
  const hasResultData = Object.keys(resultData).length > 0;
  const runtimeArtifacts = node.runtimeArtifacts ?? null;

  return (
    <aside className="inspector">
      <NodeMeta node={node} />
      <div className="card inspector__panel">
        <header className="card__header">
          <h3>Execution State</h3>
        </header>
        {runtimeState ? (
          <>
            <dl className="data-grid inspector__meta-grid">
              <div>
                <dt>Stage</dt>
                <dd>{runtimeStage}</dd>
              </div>
              <div>
                <dt>Progress</dt>
                <dd>{runtimeProgress !== undefined ? `${Math.round(runtimeProgress * 100)}%` : "-"}</dd>
              </div>
              <div>
                <dt>Last Updated</dt>
                <dd>{runtimeUpdatedAt ?? "-"}</dd>
              </div>
            </dl>
            {runtimeMessage && <p className="text-subtle">{runtimeMessage}</p>}
            {runtimeError && (
              <details>
                <summary>Error</summary>
                <pre className="inspector__payload">
                  {JSON.stringify(runtimeError, null, 2)}
                </pre>
              </details>
            )}
          </>
        ) : (
          <p className="text-subtle inspector__payload-empty">No execution data yet.</p>
        )}
      </div>
      <div className="card inspector__panel">
        <header className="card__header">
          <h3>Runtime Artifacts</h3>
        </header>
        {runtimeArtifacts === null ? (
          <p className="text-subtle inspector__payload-empty">No artifacts produced.</p>
        ) : (
          <pre className="inspector__payload">
            {JSON.stringify(runtimeArtifacts, null, 2)}
          </pre>
        )}
      </div>
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
                      <span className="inspector__port-label">{port.label}</span>
                      {port.origin === "inferred" && <span className="badge badge--muted">inferred</span>}
                    </div>
                    {port.bindingPath && (
                      <>
                        <div className="inspector__port-binding">
                          <span className="inspector__port-binding-label">Binding</span>
                          <code className="inspector__port-code">{port.bindingPath}</code>
                        </div>
                        {port.bindingMode && (
                          <div className="inspector__port-mode">
                            Mode
                            <span className="inspector__port-mode-value">
                              {port.bindingMode.toUpperCase()}
                            </span>
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
            <h4 className="inspector__ports-heading">Outputs</h4>
            {ports.outputs.length ? (
              <ul className="inspector__port-list">
                {ports.outputs.map((port) => (
                  <li key={`output-${port.key}`} className="inspector__port">
                    <div className="inspector__port-header">
                      <span className="inspector__port-label">{port.label}</span>
                      {port.origin === "inferred" && <span className="badge badge--muted">inferred</span>}
                    </div>
                    {port.bindingPath && (
                      <>
                        <div className="inspector__port-binding">
                          <span className="inspector__port-binding-label">Binding</span>
                          <code className="inspector__port-code">{port.bindingPath}</code>
                        </div>
                        {port.bindingMode && (
                          <div className="inspector__port-mode">
                            Mode
                            <span className="inspector__port-mode-value">
                              {port.bindingMode.toUpperCase()}
                            </span>
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
