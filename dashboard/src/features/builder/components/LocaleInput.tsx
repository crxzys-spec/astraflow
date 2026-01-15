import { useId, useMemo } from "react";
import { LOCALIZED_TEXT_DEFAULT_KEY } from "../../../lib/manifestText";

type LocaleInputProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  suggestions?: string[];
  placeholder?: string;
  className?: string;
  inputClassName?: string;
};

const buildSuggestions = (suggestions: string[] | undefined) => {
  const seen = new Set<string>();
  const result: string[] = [];
  const push = (value?: string) => {
    const trimmed = value?.trim();
    if (!trimmed || seen.has(trimmed)) {
      return;
    }
    seen.add(trimmed);
    result.push(trimmed);
  };
  push(LOCALIZED_TEXT_DEFAULT_KEY);
  suggestions?.forEach(push);
  return result;
};

export const LocaleInput = ({
  label,
  value,
  onChange,
  suggestions,
  placeholder,
  className,
  inputClassName,
}: LocaleInputProps) => {
  const listId = useId();
  const options = useMemo(() => buildSuggestions(suggestions), [suggestions]);
  return (
    <label className={className}>
      <span>{label}</span>
      <input
        type="text"
        list={listId}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className={inputClassName}
      />
      <datalist id={listId}>
        {options.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>
    </label>
  );
};
