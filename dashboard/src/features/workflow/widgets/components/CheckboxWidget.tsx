import type { WidgetRendererProps } from "../registry";

export const CheckboxWidget = ({ widget, value, onChange, readOnly }: WidgetRendererProps) => (
  <div className="wf-widget wf-widget--checkbox">
    <label className="wf-widget__label">
      <input
        className="wf-widget__checkbox"
        type="checkbox"
        checked={Boolean(value)}
        onChange={(event) => onChange(event.target.checked)}
        disabled={readOnly}
      />
      <span>{widget.label}</span>
    </label>
  </div>
);
