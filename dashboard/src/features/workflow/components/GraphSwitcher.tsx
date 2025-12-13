import type { WorkflowGraphScope, WorkflowSubgraphDraftEntry, WorkflowMetadata } from "../../workflow";

interface GraphSwitcherProps {
  activeGraph: WorkflowGraphScope;
  subgraphs: WorkflowSubgraphDraftEntry[];
  workflowName?: string;
  workflowId?: string;
  canEdit?: boolean;
  onSelect: (scope: WorkflowGraphScope) => void;
  onInline?: (subgraphId: string) => void;
  inlineMessage?: { subgraphId: string; type: "success" | "error"; text: string } | null;
  workflowMetadata?: WorkflowMetadata;
  onEditMetadata?: () => void;
}

const GraphSwitcher = ({
  activeGraph,
  subgraphs,
  workflowName,
  workflowId,
  canEdit,
  onSelect,
  onInline,
  inlineMessage,
  workflowMetadata,
  onEditMetadata,
}: GraphSwitcherProps) => {
  const mainActive = activeGraph.type === "root";
  const metadata = workflowMetadata;
  return (
    <div className="graph-switcher">
      <div className="graph-switcher__section">
        <div
          role="button"
          tabIndex={0}
          className={`graph-switcher__option ${mainActive ? "is-active" : ""}`}
          aria-pressed={mainActive}
          onClick={() => onSelect({ type: "root" })}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              onSelect({ type: "root" });
            }
          }}
        >
          <div className="graph-switcher__option-primary">
            <div className="graph-switcher__option-head">
              <div>
                <span className="graph-switcher__eyebrow">PRIMARY WORKFLOW</span>
                <strong>{workflowName ?? "Untitled workflow"}</strong>
              </div>
              {canEdit && (
                <button
                  type="button"
                  className="icon-button icon-button--tip"
                  title="Edit workflow info"
                  aria-label="Edit workflow info"
                  data-label="Edit info"
                  onClick={(event) => {
                    event.stopPropagation();
                    onEditMetadata?.();
                  }}
                >
                  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 13.5v2.5h2.5L15 7.5 12.5 5z" />
                    <path d="m11 6.5 2.5 2.5" />
                  </svg>
                </button>
              )}
            </div>
            <p className="graph-switcher__helper">
              {metadata?.description || "Add a short summary to describe this workflow."}
            </p>
            <p className="graph-switcher__helper">Drag nodes from the catalog to build the main flow.</p>
          </div>
          <div className="graph-switcher__meta">
            <code>{workflowId}</code>
          </div>
        </div>
      </div>
      <div className="graph-switcher__section">
        <div className="graph-switcher__section-heading">
          <h4>Subgraphs</h4>
          <span className="graph-switcher__count">{subgraphs.length}</span>
        </div>
        {subgraphs.length ? (
          <div className="graph-switcher__list">
            {subgraphs.map((entry) => {
              const isActive = activeGraph.type === "subgraph" && activeGraph.subgraphId === entry.id;
              const label = entry.definition.metadata?.name ?? entry.definition.id;
              const description = entry.metadata?.description ?? entry.definition.metadata?.description;
              const nodeCount = Object.keys(entry.definition.nodes).length;
              return (
                <div
                  key={entry.id}
                  role="button"
                  tabIndex={0}
                  className={`graph-switcher__option ${isActive ? "is-active" : ""}`}
                  aria-pressed={isActive}
                  onClick={() => onSelect({ type: "subgraph", subgraphId: entry.id })}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect({ type: "subgraph", subgraphId: entry.id });
                    }
                  }}
                >
                  <div className="graph-switcher__option-primary">
                    <div className="graph-switcher__option-head">
                      <div>
                        <span className="graph-switcher__eyebrow">CONTAINER TARGET</span>
                        <strong>{label}</strong>
                      </div>
                      {typeof onInline === "function" && (
                        <button
                          type="button"
                          className="icon-button icon-button--tip"
                          onClick={(event) => {
                            event.stopPropagation();
                            onInline(entry.id);
                          }}
                          title="Dissolve this subgraph"
                          aria-label="Dissolve subgraph"
                          data-label="Dissolve"
                        >
                          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                            <path d="m6 6 8 8" />
                            <path d="m14 6-8 8" />
                          </svg>
                        </button>
                      )}
                    </div>
                    {description && <p className="graph-switcher__helper">{description}</p>}
                    {inlineMessage && inlineMessage.subgraphId === entry.id && (
                      <small
                        className={
                          inlineMessage.type === "error" ? "error" : "text-subtle"
                        }
                      >
                        {inlineMessage.text}
                      </small>
                    )}
                  </div>
                  <div className="graph-switcher__meta graph-switcher__meta--subgraph">
                    <div className="graph-switcher__meta-id">
                      <code>{entry.id}</code>
                    </div>
                  </div>
                  <div className="graph-switcher__meta graph-switcher__meta--subgraph">
                    <div className="graph-switcher__meta-stack">
                      <span className="graph-switcher__pill graph-switcher__pill--nodes">
                        <span className="graph-switcher__pill-dot" aria-hidden="true"></span>
                        {nodeCount} nodes
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="graph-switcher__empty">
            No localized subgraphs yet. Container nodes referencing reusable workflows will be managed here.
          </p>
        )}
      </div>
    </div>
  );
};

export default GraphSwitcher;
