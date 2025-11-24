import clsx from "clsx";
import { memo, useCallback } from "react";
import { Panel, useReactFlow, useStore, useStoreApi } from "reactflow";

const WorkflowControls = memo(() => {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const store = useStoreApi();
  const minZoomReached = useStore((state) => state.transform[2] <= state.minZoom);
  const maxZoomReached = useStore((state) => state.transform[2] >= state.maxZoom);
  const isInteractive = useStore(
    (state) => state.nodesDraggable || state.nodesConnectable || state.elementsSelectable
  );

  const toggleInteractive = useCallback(() => {
    const next = !isInteractive;
    store.setState({
      nodesDraggable: next,
      nodesConnectable: next,
      elementsSelectable: next,
    });
  }, [isInteractive, store]);

  return (
    <Panel position="top-right" className="react-flow__controls workflow-controls">
      <button
        type="button"
        className="workflow-controls__btn"
        aria-label="Zoom in"
        title="Zoom in"
        onClick={zoomIn}
        disabled={maxZoomReached}
      >
        <span aria-hidden className="workflow-controls__icon workflow-controls__icon--plus" />
      </button>
      <button
        type="button"
        className="workflow-controls__btn"
        aria-label="Zoom out"
        title="Zoom out"
        onClick={zoomOut}
        disabled={minZoomReached}
      >
        <span aria-hidden className="workflow-controls__icon workflow-controls__icon--minus" />
      </button>
      <button
        type="button"
        className="workflow-controls__btn"
        aria-label="Fit view"
        title="Fit view"
        onClick={() => fitView({ padding: 0.2 })}
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
        onClick={toggleInteractive}
      >
        <span aria-hidden className="workflow-controls__icon workflow-controls__icon--interactive" />
      </button>
    </Panel>
  );
});

WorkflowControls.displayName = "WorkflowControls";

export default WorkflowControls;
