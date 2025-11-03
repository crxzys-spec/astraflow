import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import type { PackageSummary } from "../../../api/models/packageSummary";
import {
  WORKFLOW_NODE_DRAG_FORMAT,
  WORKFLOW_NODE_DRAG_PACKAGE_KEY,
  WORKFLOW_NODE_DRAG_TYPE_KEY,
  WORKFLOW_NODE_DRAG_VERSION_KEY
} from "../constants";

export interface PaletteNode {
  type: string;
  label: string;
  category: string;
  description?: string;
  tags?: string[];
  status?: string;
}

interface WorkflowPaletteProps {
  packages: PackageSummary[];
  selectedPackageName?: string;
  selectedVersion?: string;
  onSelectPackage: (packageName: string) => void;
  onSelectVersion: (version: string) => void;
  nodes: PaletteNode[];
  isLoadingPackages: boolean;
  isLoadingNodes: boolean;
  packagesError?: Error;
  nodesError?: Error;
  onRetryPackages?: () => void;
  onRetryNodes?: () => void;
}

interface PaletteSection {
  id: string;
  label: string;
  nodes: PaletteNode[];
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
        setIsOpen(false);
      }
    };
    const handleKeydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeydown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeydown);
    };
  }, [isOpen]);

  useEffect(() => {
    const selectedIndex = options.findIndex((option) => option.value === value && !option.disabled);
    if (selectedIndex >= 0) {
      setHighlightedIndex(selectedIndex);
      return;
    }
    setHighlightedIndex(options.findIndex((option) => !option.disabled));
  }, [options, value]);

  const closeMenu = useCallback(() => {
    setIsOpen(false);
  }, []);

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

  const handleControlKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLButtonElement>) => {
      if (disabled) {
        return;
      }
      if (event.key === "Tab") {
        closeMenu();
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
        aria-hidden={!isOpen}
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

const groupByCategory = (nodes: PaletteNode[]): PaletteSection[] => {
  const grouped = new Map<string, PaletteNode[]>();
  nodes.forEach((node) => {
    const category = node.category ?? "uncategorised";
    const list = grouped.get(category) ?? [];
    list.push(node);
    grouped.set(category, list);
  });
  return Array.from(grouped.entries())
    .map(([id, items]) => ({
      id,
      label: id.replace(/_/g, " "),
      nodes: items.sort((a, b) => a.label.localeCompare(b.label))
    }))
    .sort((a, b) => a.label.localeCompare(b.label));
};

export const WorkflowPalette = ({
  packages,
  selectedPackageName,
  selectedVersion,
  onSelectPackage,
  onSelectVersion,
  nodes,
  isLoadingPackages,
  isLoadingNodes,
  packagesError,
  nodesError,
  onRetryPackages,
  onRetryNodes
}: WorkflowPaletteProps) => {
  const selectedPackage = useMemo(
    () => packages.find((pkg) => pkg.name === selectedPackageName),
    [packages, selectedPackageName]
  );
  const sections = useMemo(() => groupByCategory(nodes), [nodes]);
  const versionOptions = useMemo(() => selectedPackage?.versions ?? [], [selectedPackage]);

  const packageLabelId = useId();
  const versionLabelId = useId();
  const packageControlId = useId();
  const versionControlId = useId();

  const packageOptions = useMemo(
    () =>
      packages.map((pkg) => ({
        value: pkg.name,
        label: pkg.name
      })),
    [packages]
  );

  const versionSelectOptions = useMemo(
    () =>
      versionOptions.map((version) => ({
        value: version,
        label: version
      })),
    [versionOptions]
  );

  const packagePlaceholder = useMemo(() => {
    if (isLoadingPackages) {
      return "Loading packages…";
    }
    if (!packages.length) {
      return "No packages available";
    }
    return "Select package";
  }, [isLoadingPackages, packages.length]);

  const packageNoOptionsMessage = isLoadingPackages ? "Loading packages…" : "No packages available";

  const versionPlaceholder = useMemo(() => {
    if (!selectedPackageName) {
      return "Select a package first";
    }
    if (isLoadingNodes) {
      return "Loading versions…";
    }
    if (!versionOptions.length) {
      return "No versions available";
    }
    return "Select version";
  }, [isLoadingNodes, selectedPackageName, versionOptions.length]);

  const versionNoOptionsMessage = !selectedPackageName ? "Select a package to load versions" : "No versions available";

  const handlePackageChange = useCallback(
    (packageName: string) => {
      onSelectPackage(packageName);
    },
    [onSelectPackage]
  );

  const handleVersionChange = useCallback(
    (version: string) => {
      onSelectVersion(version);
    },
    [onSelectVersion]
  );

  const handleRetryPackages = useCallback(() => {
    onRetryPackages?.();
  }, [onRetryPackages]);
  const handleRetryNodes = useCallback(() => {
    onRetryNodes?.();
  }, [onRetryNodes]);

  const combinedError = packagesError ?? nodesError;

  return (
    <aside className="palette">
      <div className="card palette__header">
        <header className="card__header">
          <h3>Catalog</h3>
          {onRetryPackages && (
            <button
              className="btn btn--ghost"
              type="button"
              onClick={handleRetryPackages}
              disabled={isLoadingPackages}
            >
              Refresh
            </button>
          )}
        </header>
        <div className="palette__controls">
          <div className="palette__control">
            <span id={packageLabelId}>Package</span>
            <PaletteSelect
              id={packageControlId}
              ariaLabelledBy={packageLabelId}
              value={selectedPackageName ?? ""}
              onChange={handlePackageChange}
              options={packageOptions}
              placeholder={packagePlaceholder}
              disabled={isLoadingPackages || !packages.length}
              noOptionsMessage={packageNoOptionsMessage}
            />
          </div>
          <div className="palette__control">
            <span id={versionLabelId}>Version</span>
            <PaletteSelect
              id={versionControlId}
              ariaLabelledBy={versionLabelId}
              value={selectedVersion ?? ""}
              onChange={handleVersionChange}
              options={versionSelectOptions}
              placeholder={versionPlaceholder}
              disabled={!selectedPackageName || isLoadingNodes || !versionOptions.length}
              noOptionsMessage={versionNoOptionsMessage}
            />
          </div>
        </div>
        {selectedPackage?.description && (
          <p className="text-subtle palette__description">{selectedPackage.description}</p>
        )}
        {isLoadingPackages && <p className="text-subtle">Loading packages...</p>}
        {!isLoadingPackages && isLoadingNodes && <p className="text-subtle">Loading nodes...</p>}
        {combinedError && (
          <p className="error">
            Failed to load catalog: {combinedError.message}
            {onRetryNodes && !isLoadingNodes && (
              <button className="btn btn--link" type="button" onClick={handleRetryNodes}>
                Retry
              </button>
            )}
          </p>
        )}
      </div>

      <div className="palette__sections">
        {sections.map((section) => (
          <div key={section.id} className="card palette__section">
            <header className="palette__section-header">
              <h4>{section.label}</h4>
              <span className="palette__count">{section.nodes.length}</span>
            </header>
            <div className="palette__items">
              {section.nodes.map((node) => (
                <button
                  key={node.type}
                  type="button"
                  className="palette__item"
                  draggable
                  onDragStart={(event) => {
                    event.dataTransfer.effectAllowed = "copy";
                    event.dataTransfer.setData(
                      WORKFLOW_NODE_DRAG_FORMAT,
                      JSON.stringify({
                        [WORKFLOW_NODE_DRAG_TYPE_KEY]: node.type,
                        [WORKFLOW_NODE_DRAG_PACKAGE_KEY]: selectedPackageName,
                        [WORKFLOW_NODE_DRAG_VERSION_KEY]: selectedVersion
                      })
                    );
                  }}
                >
                  <span className="palette__item-label">{node.label}</span>
                  <span className="palette__item-type">{node.type}</span>
                  {node.description && (
                    <p className="palette__item-description">{node.description}</p>
                  )}
                  {node.status && <span className="palette__item-status">{node.status}</span>}
                </button>
              ))}
            </div>
          </div>
        ))}
        {!isLoadingPackages && !isLoadingNodes && !combinedError && !sections.length && (
          <div className="card palette__empty">
            <p className="text-subtle">No nodes available. Check worker packages or refresh.</p>
          </div>
        )}
      </div>
    </aside>
  );
};

export default WorkflowPalette;
