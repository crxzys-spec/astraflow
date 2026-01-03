import type { FitViewOptions } from "reactflow";
import { create } from "zustand";

type FlowControlsSnapshot = {
  zoomIn?: () => void;
  zoomOut?: () => void;
  fitView?: (options?: FitViewOptions) => void;
  toggleInteractive?: () => void;
  minZoomReached: boolean;
  maxZoomReached: boolean;
  isInteractive: boolean;
  ready: boolean;
};

type FlowControlsState = FlowControlsSnapshot & {
  setControls: (controls: Partial<FlowControlsSnapshot>) => void;
  clear: () => void;
};

const defaultSnapshot: FlowControlsSnapshot = {
  zoomIn: undefined,
  zoomOut: undefined,
  fitView: undefined,
  toggleInteractive: undefined,
  minZoomReached: false,
  maxZoomReached: false,
  isInteractive: false,
  ready: false,
};

export const useFlowControlsStore = create<FlowControlsState>((set) => ({
  ...defaultSnapshot,
  setControls: (controls) => set({ ...defaultSnapshot, ...controls, ready: true }),
  clear: () => set(defaultSnapshot),
}));
