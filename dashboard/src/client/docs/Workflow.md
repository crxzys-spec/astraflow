# Workflow


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | Workflow UUID | [default to undefined]
**schemaVersion** | **string** | e.g. \&quot;2025-10\&quot; | [default to undefined]
**metadata** | [**WorkflowMetadata**](WorkflowMetadata.md) |  | [default to undefined]
**nodes** | [**Array&lt;WorkflowNode&gt;**](WorkflowNode.md) |  | [default to undefined]
**edges** | [**Array&lt;WorkflowEdge&gt;**](WorkflowEdge.md) |  | [default to undefined]
**tags** | **Array&lt;string&gt;** | Workflow-level tags. | [optional] [default to undefined]
**previewImage** | **string** | Base64-encoded preview of the workflow canvas. | [optional] [default to undefined]
**subgraphs** | [**Array&lt;WorkflowSubgraph&gt;**](WorkflowSubgraph.md) | Reusable workflow fragments (localized snapshots) that container nodes can reference. | [optional] [default to undefined]

## Example

```typescript
import { Workflow } from './api';

const instance: Workflow = {
    id,
    schemaVersion,
    metadata,
    nodes,
    edges,
    tags,
    previewImage,
    subgraphs,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
