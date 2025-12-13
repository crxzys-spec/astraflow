import { createContext, useContext, useMemo } from "react";
import type { ComponentType, ReactElement } from "react";
import type { WorkflowNodeDraft, NodeWidgetDefinition, WorkflowMiddlewareDraft } from "../types";

export interface WidgetRendererProps {
  node: WorkflowNodeDraft | WorkflowMiddlewareDraft;
  widget: NodeWidgetDefinition;
  value: unknown;
  onChange: (value: unknown) => void;
  readOnly: boolean;
}

export interface RegisteredWidget {
  component: ComponentType<WidgetRendererProps>;
  supports?: (widget: NodeWidgetDefinition) => boolean;
}

type WidgetMap = Map<string, RegisteredWidget>;

const createRegistry = (initial?: Iterable<[string, RegisteredWidget]>) => {
  const widgets: WidgetMap = new Map(initial);

  const register = (componentId: string, widget: RegisteredWidget) => {
    widgets.set(componentId, widget);
  };

  const resolve = (widget: NodeWidgetDefinition): RegisteredWidget | undefined => {
    const direct = widgets.get(widget.component);
    if (direct) {
      if (!direct.supports || direct.supports(widget)) {
        return direct;
      }
    }
    for (const entry of widgets.values()) {
      if (entry.supports && entry.supports(widget)) {
        return entry;
      }
    }
    return widgets.get("fallback");
  };

  const entries = () => Array.from(widgets.entries());

  return {
    register,
    resolve,
    entries
  };
};

const registry = createRegistry();

export const widgetRegistry = {
  register: registry.register,
  resolve: registry.resolve,
  entries: registry.entries
};

interface WidgetRegistryContextValue {
  resolve: (widget: NodeWidgetDefinition) => RegisteredWidget | undefined;
}

const WidgetRegistryContext = createContext<WidgetRegistryContextValue>({
  resolve: widgetRegistry.resolve
});

export const WidgetRegistryProvider = ({ children }: { children: ReactElement }) => {
  const value = useMemo(() => ({ resolve: widgetRegistry.resolve }), []);
  return <WidgetRegistryContext.Provider value={value}>{children}</WidgetRegistryContext.Provider>;
};

export const useWidgetRegistry = () => useContext(WidgetRegistryContext);
