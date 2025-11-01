import type { WidgetRendererProps } from "../registry";
import { toStringValue } from "./utils";

export const TextInputWidget = ({ widget, value, onChange, readOnly }: WidgetRendererProps) => (
  <div className="wf-widget">
    <label className="wf-widget__label">
      {widget.label}
      <input
        className="wf-widget__input"
        type="text"
        value={toStringValue(value)}
        onChange={(event) => onChange(event.target.value)}
        disabled={readOnly}
      />
    </label>
  </div>
);
