import type { WidgetRendererProps } from "../registry";

export const CheckboxWidget = ({ widget, value, onChange, readOnly }: WidgetRendererProps) => {
  const checked = Boolean(value);
  const toggleWidth = 42;
  const toggleHeight = 22;

  const containerStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    fontSize: "0.78rem",
    color: "rgba(226,232,240,0.94)",
    position: "relative",
    userSelect: "none",
  };

  const trackStyle: React.CSSProperties = {
    width: toggleWidth,
    height: toggleHeight,
    borderRadius: toggleHeight,
    background: checked ? "rgba(59,130,246,0.6)" : "rgba(148,163,184,0.35)",
    position: "relative",
    transition: "background 0.2s ease",
    opacity: readOnly ? 0.6 : 1,
  };

  const thumbStyle: React.CSSProperties = {
    position: "absolute",
    top: 3,
    left: checked ? toggleWidth - toggleHeight + 2 : 2,
    width: toggleHeight - 6,
    height: toggleHeight - 6,
    borderRadius: "50%",
    background: "#0f172a",
    boxShadow: "0 4px 8px rgba(15,23,42,0.45)",
    transition: "left 0.2s ease",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };

  return (
    <div className="wf-widget wf-widget--checkbox">
      <label
        style={containerStyle}
        className="wf-widget__checkbox-row"
        aria-disabled={readOnly}
      >
        <span>{widget.label}</span>
        <span aria-hidden="true" style={trackStyle}>
          <span style={thumbStyle}>
            {checked && (
              <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                <path
                  d="M1 4.5 3.3 7l5.5-6"
                  stroke="rgba(248,250,252,0.9)"
                  strokeWidth="1.35"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </span>
        </span>
        <input
          type="checkbox"
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
          disabled={readOnly}
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0,
            width: "100%",
            height: "100%",
            cursor: readOnly ? "not-allowed" : "pointer",
          }}
        />
      </label>
    </div>
  );
};
