type BuilderToolbarProps = {
  canEditWorkflow: boolean;
  canPublishWorkflow: boolean;
  persistPending: boolean;
  startRunPending: boolean;
  cancelRunPending: boolean;
  cancelRunId?: string;
  activeRunId?: string;
  activeRunStatus?: string;
  onSave: () => void;
  onPublish: () => void;
  onRun: () => void;
  onCancelRun: () => void;
};

const IconSave = () => (
  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 3h8l3 3v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
    <path d="M5 3v5h8V3" />
    <path d="M7.5 12.5h5" />
  </svg>
);

const IconPublish = () => (
  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 4v9" />
    <path d="M6.5 7.5 10 4l3.5 3.5" />
    <path d="M4 15.5h12" />
  </svg>
);

const IconRun = () => (
  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 4.5v11l8-5.5-8-5.5z" />
  </svg>
);

export const BuilderToolbar = ({
  canEditWorkflow,
  canPublishWorkflow,
  persistPending,
  startRunPending,
  cancelRunPending,
  cancelRunId,
  activeRunId,
  activeRunStatus,
  onSave,
  onPublish,
  onRun,
  onCancelRun,
}: BuilderToolbarProps) => (
  <div className="builder-toolbar">
    <div className="builder-actions">
      {!canEditWorkflow && (
        <span className="builder-alert builder-alert--error">
          You have read-only access. Request workflow.editor rights to edit or run workflows.
        </span>
      )}
    </div>
    <div className="builder-actions builder-actions--buttons">
      {canEditWorkflow && (
        <button className="btn btn--ghost" type="button" onClick={onSave} disabled={persistPending}>
          <span className="btn__icon" aria-hidden="true">
            <IconSave />
          </span>
          {persistPending ? "Saving..." : "Save"}
        </button>
      )}
      {canEditWorkflow && (
        <button
          className="btn btn--ghost"
          type="button"
          onClick={onPublish}
          disabled={!canPublishWorkflow}
          title={!canPublishWorkflow ? "Save before publishing." : undefined}
        >
          <span className="btn__icon" aria-hidden="true">
            <IconPublish />
          </span>
          Publish
        </button>
      )}
      <button
        className="btn btn--ghost"
        type="button"
        onClick={onRun}
        disabled={!canEditWorkflow || startRunPending}
      >
        <span className="btn__icon" aria-hidden="true">
          <IconRun />
        </span>
        {startRunPending ? "Launching..." : "Run"}
      </button>
      {activeRunId &&
        (!activeRunStatus || !["succeeded", "failed", "cancelled"].includes(activeRunStatus)) && (
          <button
            className="btn btn--ghost"
            type="button"
            onClick={onCancelRun}
            disabled={cancelRunPending && cancelRunId === activeRunId}
          >
            <span className="btn__icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
                <rect x="5" y="5" width="10" height="10" rx="2" />
              </svg>
            </span>
            {cancelRunPending && cancelRunId === activeRunId ? "Stopping..." : "Stop"}
          </button>
        )}
    </div>
  </div>
);

export default BuilderToolbar;
