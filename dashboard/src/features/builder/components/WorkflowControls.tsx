import clsx from "clsx";
import { memo, useCallback } from "react";
import { useFlowControlsStore } from "../hooks/useFlowControls";

const WorkflowControls = memo(() => {
  const zoomIn = useFlowControlsStore((state) => state.zoomIn);
  const zoomOut = useFlowControlsStore((state) => state.zoomOut);
  const fitView = useFlowControlsStore((state) => state.fitView);
  const toggleInteractive = useFlowControlsStore((state) => state.toggleInteractive);
  const minZoomReached = useFlowControlsStore((state) => state.minZoomReached);
  const maxZoomReached = useFlowControlsStore((state) => state.maxZoomReached);
  const isInteractive = useFlowControlsStore((state) => state.isInteractive);
  const isReady = useFlowControlsStore((state) => state.ready);

  const handleZoomIn = useCallback(() => {
    zoomIn?.();
  }, [zoomIn]);

  const handleZoomOut = useCallback(() => {
    zoomOut?.();
  }, [zoomOut]);

  const handleFitView = useCallback(() => {
    fitView?.();
  }, [fitView]);

  const handleToggleInteractive = useCallback(() => {
    toggleInteractive?.();
  }, [toggleInteractive]);

  return (
    <div className="workflow-controls workflow-controls--toolbar" role="group" aria-label="Canvas controls">
      <button
        type="button"
        className="workflow-controls__btn"
        aria-label="Zoom in"
        title="Zoom in"
        onClick={handleZoomIn}
        disabled={!isReady || maxZoomReached}
      >
        <span aria-hidden className="workflow-controls__icon workflow-controls__icon--plus" />
      </button>
      <button
        type="button"
        className="workflow-controls__btn"
        aria-label="Zoom out"
        title="Zoom out"
        onClick={handleZoomOut}
        disabled={!isReady || minZoomReached}
      >
        <span aria-hidden className="workflow-controls__icon workflow-controls__icon--minus" />
      </button>
      <button
        type="button"
        className="workflow-controls__btn"
        aria-label="Fit view"
        title="Fit view"
        onClick={handleFitView}
        disabled={!isReady}
      >
        <span aria-hidden className="workflow-controls__icon workflow-controls__icon--frame" />
      </button>
      <button
        type="button"
        className={clsx("workflow-controls__btn", {
          "workflow-controls__btn--active": isInteractive,
        })}
        aria-label="Toggle interactivity"
        title="Toggle interactivity"
        onClick={handleToggleInteractive}
        disabled={!isReady}
      >
        <span aria-hidden className="workflow-controls__icon workflow-controls__icon--interactive" />
      </button>
    </div>
  );
});

WorkflowControls.displayName = "WorkflowControls";

export default WorkflowControls;
