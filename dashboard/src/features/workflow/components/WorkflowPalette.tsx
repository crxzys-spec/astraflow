import { useCallback, useMemo } from "react";
import type { ChangeEvent } from "react";
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
  const versionOptions = selectedPackage?.versions ?? [];

  const handlePackageChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      onSelectPackage(event.target.value);
    },
    [onSelectPackage]
  );

  const handleVersionChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      onSelectVersion(event.target.value);
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
          <label className="palette__control">
            <span>Package</span>
            <select
              value={selectedPackageName ?? ""}
              onChange={handlePackageChange}
              disabled={isLoadingPackages || !packages.length}
            >
              {packages.length === 0 && <option value="">No packages</option>}
              {packages.map((pkg) => (
                <option key={pkg.name} value={pkg.name}>
                  {pkg.name}
                </option>
              ))}
            </select>
          </label>
          <label className="palette__control">
            <span>Version</span>
            <select
              value={selectedVersion ?? ""}
              onChange={handleVersionChange}
              disabled={!selectedPackageName || isLoadingNodes || !versionOptions.length}
            >
              {(!versionOptions.length || !selectedPackageName) && <option value="">Select a package</option>}
              {versionOptions.map((version) => (
                <option key={version} value={version}>
                  {version}
                </option>
              ))}
            </select>
          </label>
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
