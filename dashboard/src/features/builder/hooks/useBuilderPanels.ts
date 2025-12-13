import { useCallback, useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";

const readStoredPanelWidth = (key: "paletteWidth" | "inspectorWidth", fallback: number) => {
  if (typeof window === "undefined") {
    return fallback;
  }
  const stored = localStorage.getItem(`builder.${key}`);
  if (!stored) {
    return fallback;
  }
  const parsed = Number.parseInt(stored, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
};

export const useBuilderPanels = () => {
  const [isPaletteOpen, setPaletteOpen] = useState(true);
  const [isInspectorOpen, setInspectorOpen] = useState(true);
  const [activePaletteTab, setActivePaletteTab] = useState<"catalog" | "graphs">("catalog");
  const [activeInspectorTab, setActiveInspectorTab] = useState<"inspector" | "runs">("inspector");
  const [paletteWidth, setPaletteWidth] = useState<number>(() =>
    readStoredPanelWidth("paletteWidth", 340)
  );
  const [inspectorWidth, setInspectorWidth] = useState<number>(() =>
    readStoredPanelWidth("inspectorWidth", 360)
  );

  const handlePaletteTabSelect = useCallback(
    (tab: "catalog" | "graphs") => {
      if (activePaletteTab === tab) {
        setPaletteOpen((open) => !open);
        return;
      }
      setActivePaletteTab(tab);
      setPaletteOpen(true);
    },
    [activePaletteTab]
  );

  const handleInspectorTabSelect = useCallback(
    (tab: "inspector" | "runs") => {
      if (activeInspectorTab === tab) {
        setInspectorOpen((open) => !open);
        return;
      }
      setActiveInspectorTab(tab);
      setInspectorOpen(true);
    },
    [activeInspectorTab]
  );

  const resizeStateRef = useRef<{
    type: "palette" | "inspector";
    startX: number;
    startWidth: number;
  } | null>(null);

  const handleResizeStart = useCallback(
    (type: "palette" | "inspector") => (event: ReactMouseEvent) => {
      event.preventDefault();
      event.stopPropagation();
      const startX = event.clientX;
      const startWidth = type === "palette" ? paletteWidth : inspectorWidth;
      resizeStateRef.current = { type, startX, startWidth };
      document.body.classList.add("is-resizing");
    },
    [paletteWidth, inspectorWidth]
  );

  useEffect(() => {
    const handleMove = (event: MouseEvent) => {
      const state = resizeStateRef.current;
      if (!state) {
        return;
      }
      const delta = event.clientX - state.startX;
      if (state.type === "palette") {
        const nextWidth = Math.min(800, Math.max(220, state.startWidth + delta));
        setPaletteWidth(nextWidth);
        localStorage.setItem("builder.paletteWidth", String(nextWidth));
      } else {
        const nextWidth = Math.min(820, Math.max(260, state.startWidth - delta));
        setInspectorWidth(nextWidth);
        localStorage.setItem("builder.inspectorWidth", String(nextWidth));
      }
    };
    const handleUp = () => {
      if (resizeStateRef.current) {
        resizeStateRef.current = null;
        document.body.classList.remove("is-resizing");
      }
    };
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
    };
  }, []);

  return {
    isPaletteOpen,
    setPaletteOpen,
    isInspectorOpen,
    setInspectorOpen,
    activePaletteTab,
    activeInspectorTab,
    paletteWidth,
    inspectorWidth,
    handlePaletteTabSelect,
    handleInspectorTabSelect,
    handleResizeStart,
  };
};
