import { widgetRegistry } from "../registry";
import type { NodeWidgetDefinition } from "../../types";
import { TextInputWidget } from "../components/TextInputWidget";
import { TextAreaWidget } from "../components/TextAreaWidget";
import { NumberWidget } from "../components/NumberWidget";
import { CheckboxWidget } from "../components/CheckboxWidget";
import { JsonWidget } from "../components/JsonWidget";
import { FallbackWidget } from "../components/FallbackWidget";
import { SubgraphPickerWidget } from "../components/SubgraphPickerWidget";
import { SectionWidget } from "../components/SectionWidget";
import { SubgraphJumpWidget } from "../components/SubgraphJumpWidget";
import { OptionSelectWidget } from "../components/OptionSelectWidget";
import { TypedInputWidget } from "../components/TypedInputWidget";

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
  widgetRegistry.register("subgraph-picker", { component: SubgraphPickerWidget });
  widgetRegistry.register("subgraph-jump", { component: SubgraphJumpWidget });
  widgetRegistry.register("options", { component: OptionSelectWidget });
  widgetRegistry.register("typed-input", { component: TypedInputWidget });
  widgetRegistry.register("section", { component: SectionWidget });
  widgetRegistry.register("fallback", { component: FallbackWidget });
};
