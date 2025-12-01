export interface JsonSchema {
  type?: string | string[];
  properties?: Record<string, JsonSchema>;
  items?: JsonSchema | JsonSchema[];
  default?: unknown;
  enum?: unknown[];
  const?: unknown;
  required?: string[];
}

const clone = <T>(value: T): T =>
  value === undefined ? value : (JSON.parse(JSON.stringify(value)) as T);

type SchemaLike = JsonSchema | boolean | Record<string, unknown> | null | undefined;

const unwrapSchema = (schema: SchemaLike): JsonSchema | boolean | null => {
  if (schema === undefined || schema === null) {
    return null;
  }
  if (typeof schema === "boolean") {
    return schema;
  }
  const container = schema as Record<string, unknown>;
  const candidate =
    container.actual_instance ??
    container.actualInstance ??
    container.oneof_schema_1_validator ??
    container.oneofSchema1Validator ??
    container.oneof_schema_2_validator ??
    container.oneofSchema2Validator;
  if (candidate !== undefined && candidate !== schema) {
    return unwrapSchema(candidate as SchemaLike);
  }
  return schema as JsonSchema;
};

export const buildDefaultsFromSchema = (schema?: SchemaLike): any => {
  const resolved = unwrapSchema(schema);
  if (!resolved || typeof resolved === "boolean") {
    return {};
  }

  if (resolved.default !== undefined) {
    return clone(resolved.default);
  }

  const type = Array.isArray(resolved.type) ? resolved.type[0] : resolved.type;

  switch (type) {
    case "object": {
      const result: Record<string, unknown> = {};
      if (resolved.properties) {
        for (const [key, propertySchema] of Object.entries(resolved.properties)) {
          const value = buildDefaultsFromSchema(propertySchema);
          if (value !== undefined) {
            result[key] = value;
          }
        }
      }
      return result;
    }
    case "array": {
      if (resolved.default !== undefined) {
        return clone(resolved.default);
      }
      if (Array.isArray(resolved.items)) {
        return resolved.items.map((item) => buildDefaultsFromSchema(item));
      }
      return [];
    }
    case "string": {
      if (resolved.enum?.length) {
        return resolved.enum[0];
      }
      if (resolved.const !== undefined) {
        return resolved.const;
      }
      return "";
    }
    case "number":
    case "integer": {
      if (resolved.enum?.length) {
        return resolved.enum[0];
      }
      if (resolved.const !== undefined) {
        return resolved.const;
      }
      return 0;
    }
    case "boolean": {
      if (resolved.const !== undefined) {
        return resolved.const;
      }
      if (resolved.enum?.length) {
        return Boolean(resolved.enum[0]);
      }
      return false;
    }
    case "null":
      return null;
    default: {
      if (resolved.enum?.length) {
        return resolved.enum[0];
      }
      if (resolved.const !== undefined) {
        return resolved.const;
      }
      return resolved.default ?? null;
    }
  }
};
