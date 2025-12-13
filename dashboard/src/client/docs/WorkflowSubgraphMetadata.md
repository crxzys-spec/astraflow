# WorkflowSubgraphMetadata


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**label** | **string** | Optional human-friendly label for the subgraph. | [optional] [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**referenceWorkflowId** | **string** | Original workflow id when this subgraph was created from a reference. | [optional] [default to undefined]
**referenceWorkflowName** | **string** |  | [optional] [default to undefined]
**ownerId** | **string** |  | [optional] [default to undefined]
**notes** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { WorkflowSubgraphMetadata } from './api';

const instance: WorkflowSubgraphMetadata = {
    label,
    description,
    referenceWorkflowId,
    referenceWorkflowName,
    ownerId,
    notes,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
