import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import {
  LOCALIZED_TEXT_DEFAULT_KEY,
  getLocalizedTextEntry,
  resolveLocalizedText,
  updateLocalizedTextLocale,
  type LocalizedText,
} from "../../../lib/manifestText";
import { LocaleInput } from "../components/LocaleInput";

export type MetadataFormState = { name: LocalizedText; description: LocalizedText };

export type PublishFormState = {
  version: string;
  displayName: string;
  summary: string;
  visibility: "private" | "public" | "internal";
  changelog: string;
  mode: "new" | "existing";
  slug: string;
  packageId: string;
};

export const VISIBILITY_OPTIONS: PublishFormState["visibility"][] = ["private", "internal", "public"];

const normalizeLocaleInput = (value?: string) => {
  const trimmed = (value ?? "").trim();
  if (!trimmed) {
    return LOCALIZED_TEXT_DEFAULT_KEY;
  }
  const normalized = trimmed.toLowerCase().replace("_", "-");
  if (normalized === LOCALIZED_TEXT_DEFAULT_KEY) {
    return LOCALIZED_TEXT_DEFAULT_KEY;
  }
  return trimmed;
};

const collectLocalizedKeys = (value: LocalizedText, target: Set<string>) => {
  if (!value || typeof value === "string") {
    return;
  }
  Object.keys(value).forEach((key) => target.add(key));
};

type MetadataModalProps = {
  isOpen: boolean;
  form: MetadataFormState;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onChange: (changes: Partial<MetadataFormState>) => void;
};

export const MetadataModal = ({ isOpen, form, onClose, onSubmit, onChange }: MetadataModalProps) => {
  const { i18n } = useTranslation();
  const activeLocale = i18n.resolvedLanguage ?? i18n.language ?? LOCALIZED_TEXT_DEFAULT_KEY;
  const [editLocale, setEditLocale] = useState<string>(normalizeLocaleInput(activeLocale));
  const editLocaleKey = normalizeLocaleInput(editLocale);
  const handleLocaleChange = (nextLocale: string) => setEditLocale(normalizeLocaleInput(nextLocale));
  const localeSuggestions = useMemo(() => {
    const locales = new Set<string>();
    if (activeLocale) {
      locales.add(activeLocale);
    }
    collectLocalizedKeys(form.name, locales);
    collectLocalizedKeys(form.description, locales);
    return Array.from(locales);
  }, [activeLocale, form.description, form.name]);
  const nameEntry = getLocalizedTextEntry(form.name, editLocaleKey);
  const nameValue = nameEntry ?? "";
  const namePlaceholder =
    nameEntry === undefined
      ? resolveLocalizedText(form.name, editLocaleKey) ?? "Untitled workflow"
      : undefined;
  const descriptionEntry = getLocalizedTextEntry(form.description, editLocaleKey);
  const descriptionValue = descriptionEntry ?? "";
  const descriptionPlaceholder =
    descriptionEntry === undefined
      ? resolveLocalizedText(form.description, editLocaleKey) ?? "Add a short summary"
      : undefined;

  useEffect(() => {
    if (isOpen) {
      setEditLocale(normalizeLocaleInput(activeLocale));
    }
  }, [activeLocale, isOpen]);

  if (!isOpen) {
    return null;
  }
  return (
    <div className="modal">
      <div className="modal__backdrop" onClick={onClose} />
      <form className="modal__panel card publish-modal" onSubmit={onSubmit}>
        <header className="modal__header">
          <div>
            <h3>Edit workflow info</h3>
            <p className="text-subtle">Update the name and description shown across the app.</p>
          </div>
          <button className="modal__close" type="button" onClick={onClose} aria-label="Close metadata modal">
            x
          </button>
        </header>
        <div className="publish-modal__grid">
          <div className="publish-modal__section publish-modal__field--full">
            <LocaleInput
              label="Locale"
              value={editLocaleKey}
              onChange={handleLocaleChange}
              suggestions={localeSuggestions}
              placeholder="default"
              className="publish-modal__label"
            />
            <small className="publish-modal__helper">
              Use &quot;default&quot; as the fallback. Any locale tag works (e.g. en, zh-CN).
            </small>
          </div>
          <div className="publish-modal__section publish-modal__field--full">
            <label className="publish-modal__label">
              Name
              <input
                type="text"
                value={nameValue}
                placeholder={namePlaceholder}
                onChange={(event) =>
                  onChange({ name: updateLocalizedTextLocale(form.name, editLocaleKey, event.target.value) })
                }
              />
            </label>
          </div>
          <div className="publish-modal__section publish-modal__field--full">
            <label className="publish-modal__label">
              Description
              <textarea
                value={descriptionValue}
                onChange={(event) =>
                  onChange({
                    description: updateLocalizedTextLocale(form.description, editLocaleKey, event.target.value),
                  })
                }
                placeholder={descriptionPlaceholder ?? "Add a short summary"}
                rows={4}
              />
            </label>
          </div>
        </div>
        <footer className="modal__footer">
          <button className="btn btn--ghost" type="button" onClick={onClose}>
            Cancel
          </button>
          <button className="btn" type="submit">
            Save
          </button>
        </footer>
      </form>
    </div>
  );
};

type PublishModalProps = {
  isOpen: boolean;
  form: PublishFormState;
  isValid: boolean;
  canTargetExistingPackage: boolean;
  ownedWorkflowPackages: { id: string; displayName?: string; slug?: string }[];
  workflowPackagesErrorMessage?: string | null;
  isLoadingPackages: boolean;
  publishInProgress: boolean;
  errorMessage?: string | null;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onModeChange: (mode: PublishFormState["mode"]) => void;
  onPackageSelect: (packageId: string) => void;
  onSlugChange: (slug: string) => void;
  onFormChange: (changes: Partial<PublishFormState>) => void;
};

export const PublishModal = ({
  isOpen,
  form,
  isValid,
  canTargetExistingPackage,
  ownedWorkflowPackages,
  workflowPackagesErrorMessage,
  isLoadingPackages,
  publishInProgress,
  errorMessage,
  onClose,
  onSubmit,
  onModeChange,
  onPackageSelect,
  onSlugChange,
  onFormChange,
}: PublishModalProps) => {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal">
      <div className="modal__backdrop" onClick={onClose} />
      <form className="modal__panel card publish-modal" onSubmit={onSubmit}>
        <header className="modal__header">
          <div>
            <h3>Publish workflow</h3>
            <p className="text-subtle">Snapshot the current draft into the Store.</p>
          </div>
          <button className="modal__close" type="button" onClick={onClose} aria-label="Close publish modal">
            ×
          </button>
        </header>
        <div className="publish-modal__grid">
          <div className="publish-modal__section publish-modal__field--full">
            <span className="publish-modal__label">Publish target</span>
            <div className="publish-modal__choices">
              <label className="publish-modal__choice">
                <input
                  type="radio"
                  name="publish-target"
                  value="new"
                  checked={form.mode === "new"}
                  onChange={() => onModeChange("new")}
                />
                <div>
                  <strong>Create a new package</strong>
                  <p>Assign a fresh slug and visibility.</p>
                </div>
              </label>
              <label
                className={`publish-modal__choice${canTargetExistingPackage ? "" : " publish-modal__choice--disabled"}`}
              >
                <input
                  type="radio"
                  name="publish-target"
                  value="existing"
                  checked={form.mode === "existing"}
                  onChange={() => onModeChange("existing")}
                  disabled={!canTargetExistingPackage}
                />
                <div>
                  <strong>Append to existing package</strong>
                  <p>Publish as a new semantic version.</p>
                </div>
              </label>
              {!canTargetExistingPackage && (
                <small className="publish-modal__helper">You have not published any packages yet.</small>
              )}
            </div>
          </div>
          {form.mode === "existing" ? (
            <label className="form-field publish-modal__field publish-modal__field--half">
              <span>Package</span>
              <select
                value={form.packageId}
                onChange={(event) => onPackageSelect(event.target.value)}
                disabled={isLoadingPackages || !canTargetExistingPackage}
              >
                <option value="">Select a package</option>
                {ownedWorkflowPackages.map((pkg) => (
                  <option key={pkg.id} value={pkg.id}>
                    {pkg.displayName} ({pkg.slug})
                  </option>
                ))}
              </select>
              {isLoadingPackages && (
                <small className="publish-modal__helper">Loading your packages...</small>
              )}
              {workflowPackagesErrorMessage && (
                <small className="error">Unable to load packages: {workflowPackagesErrorMessage}</small>
              )}
            </label>
          ) : (
            <label className="form-field publish-modal__field publish-modal__field--half">
              <span>Slug*</span>
              <input
                type="text"
                value={form.slug}
                onChange={(event) => onSlugChange(event.target.value)}
                placeholder="friendly-workflow-name"
              />
              <small className="publish-modal__helper">
                Used in Store URLs. Lowercase letters, numbers, and dashes only.
              </small>
            </label>
          )}
          <label className="form-field publish-modal__field">
            <span>Version*</span>
            <input
              type="text"
              value={form.version}
              onChange={(event) => onFormChange({ version: event.target.value })}
              placeholder="e.g. 1.0.0"
              required
            />
          </label>
          <label className="form-field publish-modal__field">
            <span>Display name</span>
            <input
              type="text"
              value={form.displayName}
              onChange={(event) => onFormChange({ displayName: event.target.value })}
              placeholder="Workflow title"
            />
          </label>
          <label className="form-field publish-modal__field publish-modal__field--full">
            <span>Summary</span>
            <textarea
              value={form.summary}
              onChange={(event) => onFormChange({ summary: event.target.value })}
              rows={3}
            />
          </label>
          <label className="form-field publish-modal__field">
            <span>Visibility</span>
            <select
              value={form.visibility}
              onChange={(event) =>
                onFormChange({
                  visibility: event.target.value as PublishFormState["visibility"],
                })
              }
            >
              {VISIBILITY_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field publish-modal__field publish-modal__field--full">
            <span>Changelog</span>
            <textarea
              value={form.changelog}
              onChange={(event) => onFormChange({ changelog: event.target.value })}
              rows={3}
            />
          </label>
        </div>
        {errorMessage && (
          <div className="card card--error">
            <p className="error">{errorMessage}</p>
          </div>
        )}
        <footer className="modal__footer">
          <button className="btn" type="button" onClick={onClose} disabled={publishInProgress}>
            Cancel
          </button>
          <button className="btn btn--primary" type="submit" disabled={!isValid || publishInProgress}>
            {publishInProgress ? "Publishing..." : "Publish"}
          </button>
        </footer>
      </form>
    </div>
  );
};
