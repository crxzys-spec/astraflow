
import type { WidgetRendererProps } from "../registry";
import { useWorkflowStore } from "../../store";

const baseButtonStyle: React.CSSProperties = {
  borderRadius: "0.65rem",
  border: "1px solid rgba(96, 165, 250, 0.5)",
  padding: "0.4rem 0.85rem",
  background: "linear-gradient(135deg, rgba(59,130,246,0.35), rgba(14,165,233,0.4))",
  color: "#f8fafc",
  fontSize: "0.76rem",
  fontWeight: 600,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
};

export const SubgraphJumpWidget = ({
  widget,
  value,
}: WidgetRendererProps) => {
  const setActiveGraph = useWorkflowStore((state) => state.setActiveGraph);
  const subgraphs = useWorkflowStore((state) => state.subgraphDrafts);
  const subgraphId = typeof value === "string" && value.trim().length ? value.trim() : undefined;
  const target = subgraphId ? subgraphs.find((entry) => entry.id === subgraphId) : undefined;
  const options = (widget.options as { buttonLabel?: string } | undefined) ?? {};
  const buttonLabel = typeof options.buttonLabel === "string" && options.buttonLabel.length
    ? options.buttonLabel
    : "Open subgraph";

  const handleClick = () => {
    if (target) {
      setActiveGraph({ type: "subgraph", subgraphId: target.id });
    }
  };

  return (
    <div className="wf-widget wf-widget--subgraph-jump">
      <div
        className="wf-widget__label"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span>{widget.label}</span>
        <button
          type="button"
          onClick={handleClick}
          disabled={!target}
          style={{
            ...baseButtonStyle,
            opacity: target ? 1 : 0.45,
            cursor: target ? "pointer" : "not-allowed",
          }}
        >
          {buttonLabel}
        </button>
      </div>
      {!target && (
        <p
          className="wf-widget__hint"
          style={{ marginTop: "0.35rem", fontSize: "0.7rem" }}
        >
          Select a subgraph first.
        </p>
      )}
    </div>
  );
};
