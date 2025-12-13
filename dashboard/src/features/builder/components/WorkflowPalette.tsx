import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import {
  WORKFLOW_NODE_DRAG_FORMAT,
  WORKFLOW_NODE_DRAG_PACKAGE_KEY,
  WORKFLOW_NODE_DRAG_ROLE_KEY,
  WORKFLOW_NODE_DRAG_TYPE_KEY,
  WORKFLOW_NODE_DRAG_VERSION_KEY
} from "../constants";

export interface PaletteNodeVersion {
  version: string;
  status?: string;
}

export interface PaletteNode {
  type: string;
  label: string;
  category: string;
  packageName: string;
  role?: string;
  description?: string;
  tags?: string[];
  status?: string;
  defaultVersion?: string;
  latestVersion?: string;
  versions: PaletteNodeVersion[];
}

interface WorkflowPaletteProps {
  query: string;
  onQueryChange: (value: string) => void;
  packageOptions: string[];
  selectedPackageName?: string;
  onSelectPackage: (packageName?: string) => void;
  nodes: PaletteNode[];
  isLoading: boolean;
  error?: Error;
  onRetry?: () => void;
}

interface PaletteSelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface PaletteSelectProps {
  id?: string;
  value?: string;
  onChange: (value: string) => void;
  options: PaletteSelectOption[];
  placeholder?: string;
  disabled?: boolean;
  ariaLabelledBy?: string;
  noOptionsMessage?: string;
}

const findNextEnabledIndex = (
  options: PaletteSelectOption[],
  startIndex: number,
  direction: 1 | -1
): number => {
  if (!options.length) {
    return -1;
  }
  let index = startIndex;
  for (let attempt = 0; attempt < options.length; attempt += 1) {
    index = (index + direction + options.length) % options.length;
    if (!options[index]?.disabled) {
      return index;
    }
  }
  return startIndex;
};

const findLastEnabledIndex = (options: PaletteSelectOption[]): number => {
  for (let index = options.length - 1; index >= 0; index -= 1) {
    if (!options[index]?.disabled) {
      return index;
    }
  }
  return -1;
};

const PaletteSelect = ({
  id,
  value,
  onChange,
  options,
  placeholder = "Select",
  disabled = false,
  ariaLabelledBy,
  noOptionsMessage = "No options available"
}: PaletteSelectProps) => {
  const generatedId = useId();
  const controlId = id ?? `${generatedId}-control`;
  const listboxId = `${controlId}-listbox`;
  const containerRef = useRef<HTMLDivElement>(null);
  const controlRef = useRef<HTMLButtonElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(() => {
    const selectedIndex = options.findIndex((option) => option.value === value && !option.disabled);
    if (selectedIndex >= 0) {
      return selectedIndex;
    }
    return options.findIndex((option) => !option.disabled);
  });

  const selectedOption = useMemo(
    () => options.find((option) => option.value === value),
    [options, value]
  );

  const closeMenu = useCallback(
    (options?: { returnFocus?: boolean }) => {
      setIsOpen(false);
      if (options?.returnFocus !== false) {
        controlRef.current?.focus();
      }
    },
    []
  );

  const openMenu = useCallback(() => {
    if (disabled) {
      return;
    }
    setIsOpen(true);
    const selectedIndex = options.findIndex((option) => option.value === value && !option.disabled);
    if (selectedIndex >= 0) {
      setHighlightedIndex(selectedIndex);
      return;
    }
    setHighlightedIndex(options.findIndex((option) => !option.disabled));
  }, [disabled, options, value]);

  useEffect(() => {
    if (disabled && isOpen) {
      setIsOpen(false);
    }
  }, [disabled, isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const handleMouseDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        closeMenu({ returnFocus: false });
      }
    };
    const handleKeydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeMenu();
      }
    };
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeydown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeydown);
    };
  }, [closeMenu, isOpen]);

  useEffect(() => {
    const selectedIndex = options.findIndex((option) => option.value === value && !option.disabled);
    if (selectedIndex >= 0) {
      setHighlightedIndex(selectedIndex);
      return;
    }
    setHighlightedIndex(options.findIndex((option) => !option.disabled));
  }, [options, value]);

  const handleControlKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLButtonElement>) => {
      if (disabled) {
        return;
      }
      if (event.key === "Tab") {
        closeMenu({ returnFocus: false });
        return;
      }
      if (event.key === "Escape") {
        if (isOpen) {
          event.preventDefault();
          closeMenu();
        }
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        if (!isOpen) {
          openMenu();
          return;
        }
        const nextIndex = findNextEnabledIndex(options, highlightedIndex, 1);
        if (nextIndex >= 0) {
          setHighlightedIndex(nextIndex);
        }
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        if (!isOpen) {
          openMenu();
          return;
        }
        const nextIndex = findNextEnabledIndex(options, highlightedIndex, -1);
        if (nextIndex >= 0) {
          setHighlightedIndex(nextIndex);
        }
        return;
      }
      if (event.key === "Home") {
        event.preventDefault();
        if (!isOpen) {
          openMenu();
          return;
        }
        const firstEnabled = options.findIndex((option) => !option.disabled);
        setHighlightedIndex(firstEnabled);
        return;
      }
      if (event.key === "End") {
        event.preventDefault();
        if (!isOpen) {
          openMenu();
          return;
        }
        setHighlightedIndex(findLastEnabledIndex(options));
        return;
      }
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (!isOpen) {
          openMenu();
          return;
        }
        const option = options[highlightedIndex];
        if (option && !option.disabled) {
          onChange(option.value);
          closeMenu();
        }
      }
    },
    [closeMenu, disabled, highlightedIndex, isOpen, onChange, openMenu, options]
  );

  const handleOptionClick = useCallback(
    (option: PaletteSelectOption) => {
      if (option.disabled) {
        return;
      }
      onChange(option.value);
      closeMenu();
    },
    [closeMenu, onChange]
  );

  const handleOptionHover = useCallback((index: number, option: PaletteSelectOption) => {
    if (option.disabled) {
      return;
    }
    setHighlightedIndex(index);
  }, []);

  const rootClassName = [
    "palette-select",
    isOpen ? "palette-select--open" : "",
    disabled ? "palette-select--disabled" : ""
  ]
    .filter(Boolean)
    .join(" ");

  const controlClassName = [
    "palette-select__control",
    !selectedOption ? "palette-select__control--placeholder" : ""
  ]
    .filter(Boolean)
    .join(" ");

  const displayLabel = selectedOption?.label ?? placeholder;

  const hasEnabledOptions = options.some((option) => !option.disabled);

  return (
    <div className={rootClassName} ref={containerRef}>
      <button
        id={controlId}
        type="button"
        ref={controlRef}
        className={controlClassName}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-labelledby={ariaLabelledBy ? `${ariaLabelledBy} ${controlId}` : controlId}
        aria-controls={listboxId}
        onClick={() => {
          if (isOpen) {
            closeMenu();
          } else {
            openMenu();
          }
        }}
        onKeyDown={handleControlKeyDown}
        disabled={disabled}
      >
        <span
          className={[
            "palette-select__value",
            !selectedOption ? "palette-select__value--placeholder" : ""
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {displayLabel}
        </span>
        <span className="palette-select__chevron" aria-hidden="true" />
      </button>
      <div
        id={listboxId}
        role="listbox"
        className="palette-select__menu"
        aria-labelledby={ariaLabelledBy ?? controlId}
        data-open={isOpen}
        tabIndex={-1}
      >
        {hasEnabledOptions ? (
          options.map((option, index) => {
            const optionClassName = [
              "palette-select__option",
              option.value === value ? "palette-select__option--selected" : "",
              index === highlightedIndex ? "palette-select__option--highlighted" : "",
              option.disabled ? "palette-select__option--disabled" : ""
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <button
                key={`${option.value}-${index}`}
                type="button"
                role="option"
                id={`${listboxId}-option-${index}`}
                aria-selected={option.value === value}
                aria-disabled={option.disabled || undefined}
                tabIndex={-1}
                className={optionClassName}
                onMouseEnter={() => handleOptionHover(index, option)}
                onClick={() => handleOptionClick(option)}
              >
                {option.label}
              </button>
            );
          })
        ) : (
          <div className="palette-select__empty" role="note">
            {noOptionsMessage}
          </div>
        )}
      </div>
    </div>
  );
};

const getPaletteNodeKey = (node: PaletteNode) => `${node.packageName}::${node.type}`;

const getDefaultVersionForNode = (node: PaletteNode): string => {
  if (node.defaultVersion) {
    return node.defaultVersion;
  }
  if (node.latestVersion) {
    return node.latestVersion;
  }
  return node.versions[0]?.version ?? "";
};

export const WorkflowPalette = ({
  query,
  onQueryChange,
  packageOptions,
  selectedPackageName,
  onSelectPackage,
  nodes,
  isLoading,
  error,
  onRetry
}: WorkflowPaletteProps) => {
  const packageLabelId = useId();
  const packageControlId = useId();
  const filterControlId = useId();
  const versionControlPrefix = useId();
  const roleLabelId = useId();
  const [roleFilter, setRoleFilter] = useState<"all" | "node" | "container" | "middleware">("all");

  const [versionSelections, setVersionSelections] = useState<Record<string, string>>({});

  const packageSelectOptions = useMemo(() => {
    const options = packageOptions.map((pkg) => ({ value: pkg, label: pkg }));
    return [{ value: "", label: "All packages" }, ...options];
  }, [packageOptions]);

  useEffect(() => {
    setVersionSelections((previous) => {
      const next = { ...previous };
      const keys = new Set<string>();
      nodes.forEach((node) => {
        const key = getPaletteNodeKey(node);
        keys.add(key);
        if (!next[key]) {
          next[key] = getDefaultVersionForNode(node);
        }
      });
      Object.keys(next).forEach((key) => {
        if (!keys.has(key)) {
          delete next[key];
        }
      });
      return next;
    });
  }, [nodes]);

  const filteredNodes = useMemo(() => {
    if (roleFilter === "all") {
      return nodes;
    }
    return nodes.filter((node) => (node.role ?? "node").toLowerCase() === roleFilter);
  }, [nodes, roleFilter]);

  const roleOptions: PaletteSelectOption[] = [
    { value: "all", label: "All types" },
    { value: "node", label: "Nodes" },
    { value: "container", label: "Containers" },
    { value: "middleware", label: "Middlewares" }
  ];

  const handlePackageChange = useCallback(
    (packageName: string) => {
      onSelectPackage(packageName || undefined);
    },
    [onSelectPackage]
  );

  const handleVersionChange = useCallback((nodeKey: string, version: string) => {
    setVersionSelections((previous) => ({
      ...previous,
      [nodeKey]: version || previous[nodeKey]
    }));
  }, []);

  const hasResults = filteredNodes.length > 0;

  return (
    <aside className="palette">
      <div className="card palette__header">
        <header className="palette__header-row">
          <div className="palette__filter palette__filter--inline">
            <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
              <path
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m12.5 12.5 3 3"
              />
              <circle
                cx="9"
                cy="9"
                r="4.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
              />
            </svg>
            <input
              id={filterControlId}
              type="text"
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Search nodes (system + workers)"
              aria-label="Search catalog nodes"
            />
            {onRetry && (
              <button
                className="palette__filter-action"
                type="button"
                onClick={onRetry}
                disabled={isLoading}
                title="Refresh catalog"
                aria-label="Refresh catalog"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M20 4v5h-5" />
                  <path d="M4 20v-5h5" />
                  <path d="M5 9a7 7 0 0 1 11.2-2.8L20 9" />
                  <path d="M19 15a7 7 0 0 1-11.2 2.8L4 15" />
                </svg>
              </button>
            )}
          </div>
        </header>
        <div className="palette__controls palette__controls--grid">
          <div className="palette__control palette__control--inline">
            <span id={packageLabelId}>Package</span>
            <PaletteSelect
              id={packageControlId}
              ariaLabelledBy={packageLabelId}
              value={selectedPackageName ?? ""}
              onChange={handlePackageChange}
              options={packageSelectOptions}
              placeholder="All packages"
              disabled={isLoading || !packageSelectOptions.length}
              noOptionsMessage="No packages in results"
            />
          </div>
          <div className="palette__control palette__control--inline">
            <span id={roleLabelId}>Type</span>
            <PaletteSelect
              ariaLabelledBy={roleLabelId}
              value={roleFilter}
              onChange={(value) => setRoleFilter((value as typeof roleFilter) ?? "all")}
              options={roleOptions}
              placeholder="All types"
            />
          </div>
        </div>
        {isLoading && <p className="text-subtle">Loading catalog...</p>}
        {error && (
          <p className="error">
            Failed to load catalog: {error.message}
            {onRetry && !isLoading && (
              <button className="btn btn--link" type="button" onClick={onRetry}>
                Retry
              </button>
            )}
          </p>
        )}
      </div>

      <div className="card palette__section palette__section--flat">
        <header className="palette__section-header palette__section-header--compact">
          <div className="palette__section-title">
            <h4>Catalog</h4>
            <span className="palette__count">{filteredNodes.length}</span>
          </div>
        </header>

        <div className="palette__items palette__items--grid">
          {filteredNodes.map((node) => {
            const nodeKey = getPaletteNodeKey(node);
            const selectedVersion = versionSelections[nodeKey] ?? getDefaultVersionForNode(node);
            const versionOptions = (node.versions ?? []).map((version) => ({
              value: version.version,
              label: version.version
            }));
            const roleLabel =
              (node.role ?? "node").toLowerCase() === "middleware"
                ? "MIDDLEWARE"
                : (node.role ?? "node").toLowerCase() === "container"
                  ? "CONTAINER"
                  : "NODE";
            return (
              <div
                key={nodeKey}
                className="palette__item palette__item--compact"
                draggable
                role="button"
                tabIndex={0}
                onDragStart={(event) => {
                  event.dataTransfer.effectAllowed = "copy";
                  const payload = JSON.stringify({
                    [WORKFLOW_NODE_DRAG_TYPE_KEY]: node.type,
                    [WORKFLOW_NODE_DRAG_PACKAGE_KEY]: node.packageName,
                    [WORKFLOW_NODE_DRAG_ROLE_KEY]: node.role,
                    [WORKFLOW_NODE_DRAG_VERSION_KEY]: selectedVersion
                  });
                  event.dataTransfer.setData(WORKFLOW_NODE_DRAG_FORMAT, payload);
                  event.dataTransfer.setData("application/reactflow", payload);
                  event.dataTransfer.setData("text/plain", payload);
                }}
              >
                <div className="palette__item-row">
                  <div className="palette__item-title">
                    <span className="palette__item-label">{node.label}</span>
                    <span className="palette__item-type">{node.type}</span>
                  </div>
                  <div className="palette__item-badges">
                    <div className="palette__item-badges-row">
                      <span className="palette__pill">{roleLabel}</span>
                    </div>
                    <div className="palette__item-badges-row palette__item-badges-row--version">
                      <PaletteSelect
                        id={`${versionControlPrefix}-${nodeKey}`}
                        value={selectedVersion}
                        onChange={(value) => handleVersionChange(nodeKey, value)}
                        options={versionOptions}
                        placeholder="Version"
                        disabled={!versionOptions.length}
                        noOptionsMessage="No versions"
                      />
                    </div>
                  </div>
                </div>
                <div className="palette__item-sub">
                  <span className="palette__item-package">{node.packageName}</span>
                  {node.tags?.slice(0, 2).map((tag) => (
                    <span key={tag} className="palette__tag">
                      {tag}
                    </span>
                  ))}
                </div>
                {node.description && (
                  <p className="palette__item-description palette__item-description--clamp">
                    {node.description}
                  </p>
                )}
              </div>
            );
          })}
          {!isLoading && !error && !hasResults && (
            <div className="palette__empty">
              <p className="text-subtle">No nodes available. Check workers or adjust search.</p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

export default WorkflowPalette;
