# WorkflowMetadata


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** |  | [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**environment** | **string** |  | [optional] [default to undefined]
**namespace** | **string** | Logical workflow namespace used for indexing/cross-workflow bindings. Defaults to \&quot;default\&quot;. | [optional] [default to undefined]
**originId** | **string** | Identifier linking versions of the same workflow. By default equals the workflow id. | [optional] [default to undefined]
**ownerId** | **string** | User id that owns the workflow definition. | [optional] [default to undefined]
**ownerName** | **string** | Display name of the owner if available. | [optional] [default to undefined]
**createdBy** | **string** | User id that created the workflow definition. | [optional] [default to undefined]
**updatedBy** | **string** | User id that most recently updated the workflow definition. | [optional] [default to undefined]

## Example

```typescript
import { WorkflowMetadata } from './api';

const instance: WorkflowMetadata = {
    name,
    description,
    tags,
    environment,
    namespace,
    originId,
    ownerId,
    ownerName,
    createdBy,
    updatedBy,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
