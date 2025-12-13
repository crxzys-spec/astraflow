# WorkflowMiddleware


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | Middleware UUID | [default to undefined]
**type** | **string** | e.g. \&quot;middleware.loop\&quot; | [default to undefined]
**role** | **string** | Execution role of the middleware (always middleware). | [optional] [default to undefined]
**_package** | [**NodePackage**](NodePackage.md) |  | [default to undefined]
**status** | **string** | Middleware lifecycle state. | [default to undefined]
**category** | **string** | Group/category shown in the builder palette. | [default to undefined]
**label** | **string** |  | [default to undefined]
**description** | **string** | Longer description of the middleware behaviour. | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** | Keywords for search/filter. | [optional] [default to undefined]
**parameters** | **{ [key: string]: any; }** | Default parameter payload seeded from the manifest schema. | [optional] [default to undefined]
**results** | **{ [key: string]: any; }** | Default results payload seeded from the manifest schema. | [optional] [default to undefined]
**state** | [**WorkflowNodeState**](WorkflowNodeState.md) |  | [optional] [default to undefined]
**schema** | [**WorkflowNodeSchema**](WorkflowNodeSchema.md) |  | [optional] [default to undefined]
**ui** | [**NodeUI**](NodeUI.md) |  | [optional] [default to undefined]

## Example

```typescript
import { WorkflowMiddleware } from './api';

const instance: WorkflowMiddleware = {
    id,
    type,
    role,
    _package,
    status,
    category,
    label,
    description,
    tags,
    parameters,
    results,
    state,
    schema,
    ui,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
