import type { ChangeEvent } from "react";

import type { WidgetRendererProps } from "../registry";
import { useWorkflowStore } from "../../store";

const toStringValue = (value: unknown): string =>
  typeof value === "string" ? value : "";

export const SubgraphPickerWidget = ({
  widget,
  value,
  onChange,
  readOnly,
}: WidgetRendererProps) => {
  const subgraphs = useWorkflowStore((state) => state.subgraphDrafts);
  const selectedValue = toStringValue(value);

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const nextValue = event.target.value;
    onChange(nextValue.length > 0 ? nextValue : undefined);
  };

  return (
    <div className="wf-widget">
      <label className="wf-widget__label">
        {widget.label}
        <select
          className="wf-widget__input"
          value={selectedValue}
          onChange={handleChange}
          disabled={readOnly || subgraphs.length === 0}
        >
          <option value="">{widget.options?.placeholder ?? "Select subgraph"}</option>
          {subgraphs.map((entry) => (
            <option key={entry.id} value={entry.id}>
              {entry.metadata?.name ?? entry.id}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
};
