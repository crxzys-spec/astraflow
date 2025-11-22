import type { ReactNode } from 'react';
import { create } from 'zustand';

type ToolbarState = {
  content: ReactNode | null;
  setContent: (node: ReactNode | null) => void;
};

export const useToolbarStore = create<ToolbarState>((set) => ({
  content: null,
  setContent: (node) => set({ content: node })
}));

