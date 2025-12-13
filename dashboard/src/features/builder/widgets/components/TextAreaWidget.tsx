import clsx from "clsx";
import type { ChangeEvent, WheelEvent } from "react";
import type { WidgetRendererProps } from "../registry";
import { toStringValue } from "./utils";

export const TextAreaWidget = ({ widget, value, onChange, readOnly }: WidgetRendererProps) => {
  const rows = widget.options?.rows ? Number(widget.options.rows) : 4;
  const className = clsx("wf-widget__textarea", {
    "wf-widget__textarea--readonly": readOnly,
  });

  const handleChange = readOnly
    ? undefined
    : (event: ChangeEvent<HTMLTextAreaElement>) => onChange(event.target.value);

  const handleWheel = (event: WheelEvent<HTMLTextAreaElement>) => {
    event.stopPropagation();
  };

  const handleWheelCapture = (event: WheelEvent<HTMLTextAreaElement>) => {
    event.stopPropagation();
  };

  return (
    <div className="wf-widget">
      <label className="wf-widget__label">
        {widget.label}
        <textarea
          className={className}
          value={toStringValue(value)}
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
