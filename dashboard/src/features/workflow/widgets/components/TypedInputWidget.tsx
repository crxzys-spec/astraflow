import clsx from "clsx";
import type { ChangeEvent } from "react";
import { useWorkflowStore } from "../../store";
import { getBindingValue, resolveBindingPath, setBindingValue } from "../../utils/binding";
import type { WidgetRendererProps } from "../registry";

type OptionChoice = { value: string; label?: string } | string;

const normaliseOptions = (choices?: OptionChoice[]) =>
  (choices ?? [])
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

export const TypedInputWidget = ({ widget, node, value, onChange, readOnly }: WidgetRendererProps) => {
  const store = useWorkflowStore();
  const options = (widget.options as { options?: OptionChoice[]; typePath?: string } | undefined) ?? {};
  const typePath = resolveBindingPath(options.typePath ?? "");
  const typeValue =
    typePath && node ? (getBindingValue(node, typePath) as string | undefined) ?? "string" : "string";
  const choiceList = normaliseOptions(options.options);
  const currentType = choiceList.find((c) => c.value === typeValue)?.value ?? typeValue ?? "string";

  const handleTypeChange = (event: ChangeEvent<HTMLSelectElement>) => {
    if (!typePath || !node) {
      return;
    }
    const nextType = event.target.value;
    store.updateNode(node.id, (current) => setBindingValue(current, typePath, nextType));
  };

  const handleValueChange = (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    onChange(event.target.value);
  };

  const renderInput = () => {
    if (currentType === "textarea" || currentType === "text") {
      return (
        <textarea
          id={`${widget.key}-value`}
          className={clsx("wf-widget__textarea", { "wf-widget__textarea--readonly": readOnly })}
          value={typeof value === "string" ? value : value ?? ""}
          onChange={handleValueChange}
          readOnly={readOnly}
          rows={3}
        />
      );
    }
    const isFloat = currentType === "float";
    const inputType = currentType === "number" || currentType === "float" ? "number" : "text";
    return (
      <input
        id={`${widget.key}-value`}
        className={clsx("wf-widget__input", { "wf-widget__input--readonly": readOnly })}
        type={inputType}
        step={isFloat ? "any" : undefined}
        value={value ?? ""}
        onChange={handleValueChange}
        readOnly={readOnly}
      />
    );
  };

  return (
    <div className="wf-widget wf-widget--typed-input">
      <label className="wf-widget__label" htmlFor={`${widget.key}-type`}>
        {widget.label ?? "Input"}
        <div className="wf-widget__typed">
          <select
            id={`${widget.key}-type`}
            className={clsx("wf-widget__select", { "wf-widget__select--readonly": readOnly })}
            value={currentType}
            onChange={handleTypeChange}
            disabled={readOnly}
          >
            {choiceList.map((choice) => (
              <option key={choice.value} value={choice.value}>
                {choice.label}
              </option>
            ))}
          </select>
          {renderInput()}
        </div>
      </label>
    </div>
  );
};
