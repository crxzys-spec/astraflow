import type { WidgetRendererProps } from "../registry";
import { toStringValue } from "./utils";

export const TextAreaWidget = ({ widget, value, onChange, readOnly }: WidgetRendererProps) => (
  <div className="wf-widget">
    <label className="wf-widget__label">
      {widget.label}
      <textarea
        className="wf-widget__textarea"
        value={toStringValue(value)}
        onChange={(event) => onChange(event.target.value)}
        disabled={readOnly}
        rows={widget.options?.rows ? Number(widget.options.rows) : 4}
      />
    </label>
  </div>
);
