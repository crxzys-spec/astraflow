import type { CSSProperties, ReactMouseEvent, ReactNode, Ref } from "react";

type BuilderLayoutProps = {
  palette: ReactNode;
  inspector: ReactNode;
  canvas: ReactNode;
  canvasRef?: Ref<HTMLDivElement>;
  watermarkTitle?: string;
  watermarkSubtitle?: string;
  paletteWidth: number;
  inspectorWidth: number;
  isPaletteOpen: boolean;
  isInspectorOpen: boolean;
  paletteSwitchStyle: CSSProperties;
  inspectorSwitchStyle: CSSProperties;
  paletteHandleStyle: CSSProperties;
  inspectorHandleStyle: CSSProperties;
  onPaletteResizeStart: (event: ReactMouseEvent<HTMLButtonElement>) => void;
  onInspectorResizeStart: (event: ReactMouseEvent<HTMLButtonElement>) => void;
  paletteTabs: ReactNode;
  inspectorTabs: ReactNode;
};

export const BuilderLayout = ({
  palette,
  inspector,
  canvas,
  canvasRef,
  watermarkTitle,
  watermarkSubtitle,
  paletteWidth,
  inspectorWidth,
  isPaletteOpen,
  isInspectorOpen,
  paletteSwitchStyle,
  inspectorSwitchStyle,
  paletteHandleStyle,
  inspectorHandleStyle,
  onPaletteResizeStart,
  onInspectorResizeStart,
  paletteTabs,
  inspectorTabs,
}: BuilderLayoutProps) => {
  const paletteFlyoutStyle = { width: `${paletteWidth}px` };
  const inspectorFlyoutStyle = { width: `${inspectorWidth}px` };

  return (
    <section className="builder-screen">
      <div className="builder-stage">
        <div className="builder-stage__body">
          <div className="builder-stage__canvas card card--canvas">
            <div className="builder-canvas__viewport" ref={canvasRef}>
              {canvas}
            </div>
          </div>

          <div className="palette-switch" style={paletteSwitchStyle}>
            <div className="palette-tabs" role="group" aria-label="Workflow builder panels">
              {paletteTabs}
            </div>
          </div>
          {isPaletteOpen && (
            <button
              type="button"
              className="builder-resize-handle builder-resize-handle--palette"
              onMouseDown={onPaletteResizeStart}
              aria-label="Resize catalog panel"
              style={paletteHandleStyle}
            />
          )}

          <div
            className={`builder-flyout builder-flyout--palette card card--surface ${
              isPaletteOpen ? "is-open" : "is-collapsed"
            }`}
            style={paletteFlyoutStyle}
          >
            <div className="palette-tabpanel">{palette}</div>
          </div>

          <div className="inspector-switch" style={inspectorSwitchStyle}>
            <div className="inspector-tabs-floating" role="group" aria-label="Inspector panels">
              {inspectorTabs}
            </div>
          </div>

          {isInspectorOpen && (
            <button
              type="button"
              className="builder-resize-handle builder-resize-handle--inspector"
              onMouseDown={onInspectorResizeStart}
              aria-label="Resize inspector panel"
              style={inspectorHandleStyle}
            />
          )}

          <div
            className={`builder-flyout builder-flyout--inspector card card--surface ${
              isInspectorOpen ? "is-open" : "is-collapsed"
            }`}
            style={inspectorFlyoutStyle}
          >
            <div className="inspector-panel">{inspector}</div>
          </div>
        </div>
        <div className="builder-stage__watermark">
          <span className="builder-watermark__title">{watermarkTitle ?? "Untitled Workflow"}</span>
          <span className="builder-watermark__subtitle">{watermarkSubtitle}</span>
        </div>
      </div>
    </section>
  );
};

export default BuilderLayout;
