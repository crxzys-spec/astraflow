import clsx from "clsx";
import type { ChangeEvent, WheelEvent } from "react";
import type { WidgetRendererProps } from "../registry";
import { toStringValue } from "./utils";

export const JsonWidget = ({ widget, value, onChange, readOnly }: WidgetRendererProps) => {
  const rows = widget.options?.rows ? Number(widget.options.rows) : 8;
  const className = clsx("wf-widget__textarea", "wf-widget__textarea--code", {
    "wf-widget__textarea--readonly": readOnly,
  });

  const handleChange = readOnly
    ? undefined
    : (event: ChangeEvent<HTMLTextAreaElement>) => {
        const next = event.target.value;
        try {
          onChange(next ? JSON.parse(next) : undefined);
        } catch (_error) {
          onChange(next);
        }
      };

  const handleWheel = (event: WheelEvent<HTMLTextAreaElement>) => {
    event.stopPropagation();
  };

  const handleWheelCapture = (event: WheelEvent<HTMLTextAreaElement>) => {
    event.stopPropagation();
  };

  const renderedValue = toStringValue(
    typeof value === "string" ? value : value === undefined ? "" : JSON.stringify(value, null, 2),
  );

  return (
    <div className="wf-widget">
      <label className="wf-widget__label wf-widget__label--stacked">
        {widget.label}
        <textarea
          className={className}
          value={renderedValue}
          onChange={handleChange}
          readOnly={readOnly}
          rows={rows}
          onWheel={handleWheel}
          onWheelCapture={handleWheelCapture}
        />
      </label>
    </div>
  );
};
