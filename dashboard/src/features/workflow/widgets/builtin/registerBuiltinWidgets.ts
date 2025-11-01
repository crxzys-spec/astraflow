import { widgetRegistry } from "../registry";
import type { NodeWidgetDefinition } from "../../types";
import { TextInputWidget } from "../components/TextInputWidget";
import { TextAreaWidget } from "../components/TextAreaWidget";
import { NumberWidget } from "../components/NumberWidget";
import { CheckboxWidget } from "../components/CheckboxWidget";
import { JsonWidget } from "../components/JsonWidget";
import { FallbackWidget } from "../components/FallbackWidget";

let registered = false;

const supportsBoolean = (widget: NodeWidgetDefinition) => widget.component === "boolean";

export const registerBuiltinWidgets = () => {
  if (registered) {
    return;
  }
  registered = true;

  widgetRegistry.register("text", { component: TextInputWidget });
  widgetRegistry.register("textarea", { component: TextAreaWidget });
  widgetRegistry.register("number", { component: NumberWidget });
  widgetRegistry.register("checkbox", { component: CheckboxWidget });
  widgetRegistry.register("boolean", { component: CheckboxWidget, supports: supportsBoolean });
  widgetRegistry.register("json", { component: JsonWidget });
  widgetRegistry.register("fallback", { component: FallbackWidget });
};
