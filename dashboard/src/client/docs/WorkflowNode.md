# WorkflowNode


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | Node UUID | [default to undefined]
**type** | **string** | e.g. \&quot;playwright.open_page\&quot; | [default to undefined]
**role** | **string** | Execution role of the node. | [optional] [default to undefined]
**_package** | [**NodePackage**](NodePackage.md) |  | [default to undefined]
**status** | **string** | Node lifecycle state. | [default to undefined]
**category** | **string** | Group/category shown in the builder palette. | [default to undefined]
**label** | **string** |  | [default to undefined]
**description** | **string** | Longer description of the node behaviour. | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** | Keywords for search/filter. | [optional] [default to undefined]
**position** | [**WorkflowNodePosition**](WorkflowNodePosition.md) |  | [default to undefined]
**parameters** | **{ [key: string]: any; }** | Default parameter payload seeded from the manifest schema. | [optional] [default to undefined]
**results** | **{ [key: string]: any; }** | Default results payload seeded from the manifest schema. | [optional] [default to undefined]
**state** | [**WorkflowNodeState**](WorkflowNodeState.md) |  | [optional] [default to undefined]
**schema** | [**WorkflowNodeSchema**](WorkflowNodeSchema.md) |  | [optional] [default to undefined]
**ui** | [**NodeUI**](NodeUI.md) |  | [optional] [default to undefined]
**middlewares** | [**Array&lt;WorkflowMiddleware&gt;**](WorkflowMiddleware.md) | Ordered list of middleware definitions attached to this node. | [optional] [default to undefined]

## Example

```typescript
import { WorkflowNode } from './api';

const instance: WorkflowNode = {
    id,
    type,
    role,
    _package,
    status,
    category,
    label,
    description,
    tags,
    position,
    parameters,
    results,
    state,
    schema,
    ui,
    middlewares,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
