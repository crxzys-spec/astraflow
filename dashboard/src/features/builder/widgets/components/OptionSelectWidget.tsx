import clsx from "clsx";
import type { ChangeEvent } from "react";
import { useEffect, useMemo } from "react";
import type { WidgetRendererProps } from "../registry";
import { getBindingValue, resolveBindingPath } from "../../utils/binding";

type OptionChoice = { value: string; label?: string } | string;

type OptionSelectOptions = {
  options?: OptionChoice[];
  optionsByKey?: Record<string, OptionChoice[]>;
  keyPath?: string;
  fallback?: OptionChoice[];
  autoSelectFirst?: boolean;
  includeCurrent?: boolean;
};

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

export const OptionSelectWidget = ({ widget, node, value, onChange, readOnly }: WidgetRendererProps) => {
  const config = (widget.options as OptionSelectOptions | undefined) ?? {};
  const selectorPath = resolveBindingPath(config.keyPath ?? "");
  const selectorValue =
    selectorPath && node ? getBindingValue(node, selectorPath) : undefined;
  const selectorKey =
    selectorValue === undefined || selectorValue === null ? "" : String(selectorValue);
  const baseChoices = normalizeOptions(
    config.optionsByKey?.[selectorKey] ?? config.options ?? config.fallback,
  );
  const current = value === undefined || value === null ? "" : String(value);
  const includeCurrent = config.includeCurrent ?? false;
  const shouldAutoSelect = config.autoSelectFirst ?? Boolean(config.optionsByKey);
  const choices = useMemo(() => {
    if (!includeCurrent || !current) {
      return baseChoices;
    }
    const exists = baseChoices.some((choice) => choice.value === current);
    if (exists) {
      return baseChoices;
    }
    return [...baseChoices, { value: current, label: `${current} (custom)` }];
  }, [baseChoices, current, includeCurrent]);

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onChange(event.target.value);
  };

  useEffect(() => {
    if (!shouldAutoSelect || readOnly) {
      return;
    }
    if (!baseChoices.length) {
      return;
    }
    const inBase = baseChoices.some((choice) => choice.value === current);
    if (!current || !inBase) {
      onChange(baseChoices[0].value);
    }
  }, [baseChoices, config.autoSelectFirst, current, onChange, readOnly]);

  const hasChoices = choices.length > 0;

  return (
    <div className="wf-widget">
      <label className="wf-widget__label" htmlFor={widget.key}>
        {widget.label}
        <select
          id={widget.key}
          className={clsx("wf-widget__select", { "wf-widget__select--readonly": readOnly })}
          value={current}
          onChange={handleChange}
          disabled={readOnly || !hasChoices}
        >
          {!hasChoices && <option value="">No options available</option>}
          {choices.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
};
