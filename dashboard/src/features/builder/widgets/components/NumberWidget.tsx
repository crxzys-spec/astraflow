import type { WidgetRendererProps } from "../registry";
import { toNumberValue } from "./utils";

export const NumberWidget = ({ widget, value, onChange, readOnly }: WidgetRendererProps) => (
  <div className="wf-widget">
    <label className="wf-widget__label">
      {widget.label}
      <input
        className="wf-widget__input"
        type="number"
        value={toNumberValue(value)}
        onChange={(event) =>
          onChange(event.target.value === "" ? undefined : Number(event.target.value))
        }
        disabled={readOnly}
      />
    </label>
  </div>
);
