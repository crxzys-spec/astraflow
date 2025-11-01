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

export const buildDefaultsFromSchema = (schema?: JsonSchema | null): any => {
  if (!schema) {
    return {};
  }

  if (schema.default !== undefined) {
    return clone(schema.default);
  }

  const type = Array.isArray(schema.type) ? schema.type[0] : schema.type;

  switch (type) {
    case 'object': {
      const result: Record<string, unknown> = {};
      if (schema.properties) {
        for (const [key, propertySchema] of Object.entries(schema.properties)) {
          const value = buildDefaultsFromSchema(propertySchema);
          if (value !== undefined) {
            result[key] = value;
          }
        }
      }
      return result;
    }
    case 'array': {
      if (schema.default !== undefined) {
        return clone(schema.default);
      }
      if (Array.isArray(schema.items)) {
        return schema.items.map((item) => buildDefaultsFromSchema(item));
      }
      return [];
    }
    case 'string': {
      if (schema.enum?.length) {
        return schema.enum[0];
      }
      if (schema.const !== undefined) {
        return schema.const;
      }
      return '';
    }
    case 'number':
    case 'integer': {
      if (schema.enum?.length) {
        return schema.enum[0];
      }
      if (schema.const !== undefined) {
        return schema.const;
      }
      return 0;
    }
    case 'boolean': {
      if (schema.const !== undefined) {
        return schema.const;
      }
      if (schema.enum?.length) {
        return Boolean(schema.enum[0]);
      }
      return false;
    }
    case 'null':
      return null;
    default: {
      if (schema.enum?.length) {
        return schema.enum[0];
      }
      if (schema.const !== undefined) {
        return schema.const;
      }
      return schema.default ?? null;
    }
  }
};
