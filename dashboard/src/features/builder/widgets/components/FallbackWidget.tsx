import type { WidgetRendererProps } from "../registry";

export const FallbackWidget = ({ widget, value }: WidgetRendererProps) => (
  <div className="wf-widget wf-widget--fallback">
    <div className="wf-widget__label">{widget.label}</div>
    <pre className="wf-widget__fallback-dump">{JSON.stringify(value, null, 2)}</pre>
  </div>
);
