import type { WidgetRendererProps } from "../registry";
import { toStringValue } from "./utils";

export const JsonWidget = ({ widget, value, onChange, readOnly }: WidgetRendererProps) => (
  <div className="wf-widget">
    <label className="wf-widget__label wf-widget__label--stacked">
      {widget.label}
      <textarea
        className="wf-widget__textarea wf-widget__textarea--code"
        value={toStringValue(
          typeof value === "string" ? value : value === undefined ? "" : JSON.stringify(value, null, 2)
        )}
        onChange={(event) => {
          const next = event.target.value;
          try {
            onChange(next ? JSON.parse(next) : undefined);
          } catch (error) {
            onChange(next);
          }
        }}
        disabled={readOnly}
        rows={widget.options?.rows ? Number(widget.options.rows) : 8}
      />
    </label>
  </div>
);
