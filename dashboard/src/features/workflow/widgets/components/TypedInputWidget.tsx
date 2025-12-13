import clsx from "clsx";
import type { ChangeEvent, CSSProperties } from "react";
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

  const handleBooleanChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.checked);
  };

  const renderInput = () => {
    if (currentType === "boolean") {
      const checked =
        typeof value === "boolean"
          ? value
          : typeof value === "string"
            ? value.trim().toLowerCase() === "true"
            : Boolean(value);
      const toggleWidth = 42;
      const toggleHeight = 22;
      const containerStyle: CSSProperties = {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 8,
        position: "relative",
        userSelect: "none",
        minHeight: toggleHeight,
        width: "100%",
      };
      const trackStyle: CSSProperties = {
        width: toggleWidth,
        height: toggleHeight,
        borderRadius: toggleHeight,
        background: checked ? "rgba(59,130,246,0.6)" : "rgba(148,163,184,0.35)",
        position: "relative",
        transition: "background 0.2s ease",
        opacity: readOnly ? 0.6 : 1,
        boxSizing: "border-box",
      };
      const thumbStyle: CSSProperties = {
        position: "absolute",
        top: 3,
        left: checked ? toggleWidth - toggleHeight + 2 : 2,
        width: toggleHeight - 6,
        height: toggleHeight - 6,
        borderRadius: "50%",
        background: "#0f172a",
        boxShadow: "0 4px 8px rgba(15,23,42,0.45)",
        transition: "left 0.2s ease",
      };
      return (
        <label style={containerStyle} aria-disabled={readOnly}>
          <span style={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.8)" }}>
            {checked ? "True" : "False"}
          </span>
          <span aria-hidden="true" style={trackStyle}>
            <span style={thumbStyle} />
          </span>
          <input
            id={`${widget.key}-value`}
            className={clsx("wf-widget__input", { "wf-widget__input--readonly": readOnly })}
            type="checkbox"
            checked={checked}
            onChange={handleBooleanChange}
            disabled={readOnly}
            style={{
              position: "absolute",
              inset: 0,
              opacity: 0,
              width: "100%",
              height: "100%",
              cursor: readOnly ? "not-allowed" : "pointer",
            }}
          />
        </label>
      );
    }
    if (currentType === "textarea" || currentType === "text") {
      return (
        <textarea
          id={`${widget.key}-value`}
          className={clsx("wf-widget__textarea", { "wf-widget__textarea--readonly": readOnly })}
          value={typeof value === "string" ? value : ""}
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
        value={typeof value === "number" || typeof value === "string" ? value : ""}
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
