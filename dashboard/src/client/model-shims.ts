import type { UIBindingModeEnum } from "./models/uibinding";

export const UIBindingMode = {
  read: "read",
  write: "write",
  two_way: "two_way",
} as const;

export type UIBindingMode = typeof UIBindingMode[keyof typeof UIBindingMode];

// Helpful alias to map generated enum to the simpler union.
export const toUIBindingMode = (value?: UIBindingModeEnum | string | null): UIBindingMode | undefined => {
  if (!value) return undefined;
  const normalized = value.toString().toLowerCase();
  if (normalized === "read" || normalized === "write" || normalized === "two_way") {
    return normalized as UIBindingMode;
  }
  return undefined;
};

// Placeholder type for node status metadata; generator does not emit a dedicated interface.
export type RunNodeStatusMetadata = Record<string, unknown>;
