# RunNodeStatus


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**nodeId** | **string** |  | [default to undefined]
**taskId** | **string** |  | [default to undefined]
**status** | [**RunStatus**](RunStatus.md) |  | [default to undefined]
**workerId** | **string** |  | [optional] [default to undefined]
**startedAt** | **string** |  | [optional] [default to undefined]
**finishedAt** | **string** |  | [optional] [default to undefined]
**seq** | **number** |  | [optional] [default to undefined]
**pendingAck** | **boolean** | True when the scheduler has dispatched the node and is waiting for a worker ACK. | [optional] [default to undefined]
**dispatchId** | **string** | Envelope id of the last cmd.dispatch frame for this node. | [optional] [default to undefined]
**ackDeadline** | **string** | Scheduler-side deadline for receiving the ACK for the last dispatch. | [optional] [default to undefined]
**resourceRefs** | **Array&lt;{ [key: string]: any; }&gt;** |  | [optional] [default to undefined]
**affinity** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**artifacts** | **Array&lt;{ [key: string]: any; }&gt;** |  | [optional] [default to undefined]
**result** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**state** | [**WorkflowNodeState**](WorkflowNodeState.md) |  | [optional] [default to undefined]
**error** | [**ResultError**](ResultError.md) |  | [optional] [default to undefined]

## Example

```typescript
import { RunNodeStatus } from './api';

const instance: RunNodeStatus = {
    nodeId,
    taskId,
    status,
    workerId,
    startedAt,
    finishedAt,
    seq,
    pendingAck,
    dispatchId,
    ackDeadline,
    resourceRefs,
    affinity,
    artifacts,
    result,
    metadata,
    state,
    error,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
