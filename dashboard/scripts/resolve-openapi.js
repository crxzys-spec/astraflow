import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname } from "node:path";

const BUNDLE_PATH = "tmp/openapi.bundled.json";
const OUTPUT_PATH = "tmp/openapi.resolved.json";

const ensureDir = (path) => {
  const dir = dirname(path);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
};

const normalizeNode = (value) => {
  if (typeof value === "string") {
    if (value.startsWith("#/components/x-parameters/")) {
      return value.replace("#/components/x-parameters/", "#/components/parameters/");
    }
    if (value.startsWith("#/components/x-responses/")) {
      return value.replace("#/components/x-responses/", "#/components/responses/");
    }
    return value;
  }

  if (Array.isArray(value)) {
    return value.map(normalizeNode);
  }

  if (value && typeof value === "object") {
    const next = {};
    const constValue = Object.prototype.hasOwnProperty.call(value, "const") ? value.const : undefined;

    for (const [key, val] of Object.entries(value)) {
      if (key === "const") {
        continue;
      }
      next[key] = normalizeNode(val);
    }

    if (constValue !== undefined) {
      if (!next.enum) {
        next.enum = [constValue];
      }
      if (!next.type && constValue !== null) {
        const jsType = typeof constValue;
        if (jsType === "string" || jsType === "number" || jsType === "boolean") {
          next.type = jsType === "number" && Number.isInteger(constValue) ? "integer" : jsType;
        }
      }
    }

    return next;
  }

  return value;
};

const main = () => {
  const raw = JSON.parse(readFileSync(BUNDLE_PATH, "utf8"));
  const spec = normalizeNode(raw);

  spec.openapi = "3.0.3";
  spec.components = spec.components || {};

  if (spec.components["x-parameters"]) {
    spec.components.parameters = {
      ...(spec.components.parameters || {}),
      ...spec.components["x-parameters"],
    };
    delete spec.components["x-parameters"];
  }

  if (spec.components["x-responses"]) {
    spec.components.responses = {
      ...(spec.components.responses || {}),
      ...spec.components["x-responses"],
    };
    delete spec.components["x-responses"];
  }

  ensureDir(OUTPUT_PATH);
  writeFileSync(OUTPUT_PATH, JSON.stringify(spec, null, 2));
  console.log(`Wrote ${OUTPUT_PATH}`);
};

main();
