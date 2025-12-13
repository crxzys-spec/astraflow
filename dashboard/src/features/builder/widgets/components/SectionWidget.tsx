import type { WidgetRendererProps } from "../registry";

export const SectionWidget = ({ widget }: WidgetRendererProps) => {
  const description =
    typeof widget.options === "object" && widget.options
      ? (widget.options as Record<string, unknown>).description
      : undefined;
  return (
    <div
      className="wf-widget wf-widget--section"
      style={{
        padding: "0.35rem 0",
        opacity: 0.85,
        textTransform: "uppercase",
        letterSpacing: "0.12em",
        fontSize: "0.68rem",
        color: "rgba(148,163,184,0.9)",
      }}
    >
      <div>{widget.label}</div>
      {typeof description === "string" && description.length > 0 && (
        <p style={{ margin: "0.35rem 0 0", textTransform: "none", letterSpacing: "normal" }}>
          {description}
        </p>
      )}
    </div>
  );
};
