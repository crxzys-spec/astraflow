# WorkflowSubgraph


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | Stable identifier referenced by container nodes. | [default to undefined]
**definition** | [**Workflow**](Workflow.md) |  | [default to undefined]
**metadata** | [**WorkflowSubgraphMetadata**](WorkflowSubgraphMetadata.md) |  | [optional] [default to undefined]

## Example

```typescript
import { WorkflowSubgraph } from './api';

const instance: WorkflowSubgraph = {
    id,
    definition,
    metadata,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
