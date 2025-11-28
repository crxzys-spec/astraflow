import clsx from "clsx";
import type { ChangeEvent } from "react";
import type { WidgetRendererProps } from "../registry";

type OptionChoice = { value: string; label?: string } | string;

const normalizeOptions = (choices?: OptionChoice[]): { value: string; label: string }[] => {
  if (!choices) {
    return [];
  }
  return choices
    .map((entry) => {
      if (typeof entry === "string") {
        return { value: entry, label: entry };
      }
      if (entry && typeof entry.value === "string") {
        return { value: entry.value, label: entry.label ?? entry.value };
      }
      return null;
    })
    .filter((entry): entry is { value: string; label: string } => Boolean(entry));
};

export const OptionSelectWidget = ({ widget, value, onChange, readOnly }: WidgetRendererProps) => {
  const choices = normalizeOptions((widget.options as { options?: OptionChoice[] } | undefined)?.options);
  const current = typeof value === "string" ? value : "";

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onChange(event.target.value);
  };

  return (
    <div className="widget widget--select">
      <label className="widget__label" htmlFor={widget.key}>
        {widget.label}
      </label>
      <select
        id={widget.key}
        className={clsx("widget__select", { "widget__select--readonly": readOnly })}
        value={current}
        onChange={handleChange}
        disabled={readOnly}
      >
        {choices.map((choice) => (
          <option key={choice.value} value={choice.value}>
            {choice.label}
          </option>
        ))}
      </select>
    </div>
  );
};
