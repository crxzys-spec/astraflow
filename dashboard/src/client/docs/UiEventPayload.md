# UiEventPayload


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**runId** | **string** |  | [default to undefined]
**status** | [**WorkerPackageStatus**](WorkerPackageStatus.md) |  | [default to undefined]
**startedAt** | **string** |  | [optional] [default to undefined]
**finishedAt** | **string** |  | [optional] [default to undefined]
**reason** | **string** |  | [optional] [default to undefined]
**run** | [**Run**](Run.md) |  | [default to undefined]
**nodes** | [**Array&lt;RunNodeStatus&gt;**](RunNodeStatus.md) |  | [optional] [default to undefined]
**metric** | **string** |  | [default to undefined]
**value** | **number** |  | [default to undefined]
**tags** | **{ [key: string]: string; }** |  | [optional] [default to undefined]
**nodeId** | **string** |  | [default to undefined]
**state** | [**WorkflowNodeState**](WorkflowNodeState.md) |  | [default to undefined]
**workerName** | **string** |  | [default to undefined]
**seq** | **number** |  | [optional] [default to undefined]
**ackPending** | **boolean** |  | [optional] [default to undefined]
**revision** | **number** |  | [default to undefined]
**format** | **string** |  | [optional] [default to FormatEnum_Json]
**content** | **{ [key: string]: any; }** |  | [default to undefined]
**artifacts** | [**Array&lt;RunArtifact&gt;**](RunArtifact.md) |  | [optional] [default to undefined]
**summary** | **string** |  | [optional] [default to undefined]
**complete** | **boolean** |  | [optional] [default to false]
**sequence** | **number** |  | [default to undefined]
**operation** | **string** |  | [default to undefined]
**path** | **string** |  | [optional] [default to undefined]
**payload** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**patches** | [**Array&lt;JsonPatchOperation&gt;**](JsonPatchOperation.md) |  | [optional] [default to undefined]
**chunkMeta** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**terminal** | **boolean** |  | [optional] [default to false]
**error** | [**ResultError**](ResultError.md) |  | [default to undefined]
**artifactId** | **string** |  | [default to undefined]
**url** | **string** |  | [optional] [default to undefined]
**expiresAt** | **string** |  | [optional] [default to undefined]
**sizeBytes** | **number** |  | [optional] [default to undefined]
**commandId** | **string** |  | [default to undefined]
**receivedAt** | **string** |  | [optional] [default to undefined]
**at** | **string** |  | [default to undefined]
**queues** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**instanceId** | **string** |  | [optional] [default to undefined]
**hostname** | **string** |  | [optional] [default to undefined]
**version** | **string** |  | [optional] [default to undefined]
**connected** | **boolean** |  | [optional] [default to undefined]
**registered** | **boolean** |  | [optional] [default to undefined]
**heartbeat** | [**WorkerHeartbeatSnapshot**](WorkerHeartbeatSnapshot.md) |  | [optional] [default to undefined]
**_package** | **string** |  | [default to undefined]
**message** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { UiEventPayload } from './api';

const instance: UiEventPayload = {
    kind,
    runId,
    status,
    startedAt,
    finishedAt,
    reason,
    run,
    nodes,
    metric,
    value,
    tags,
    nodeId,
    state,
    workerName,
    seq,
    ackPending,
    revision,
    format,
    content,
    artifacts,
    summary,
    complete,
    sequence,
    operation,
    path,
    payload,
    patches,
    chunkMeta,
    terminal,
    error,
    artifactId,
    url,
    expiresAt,
    sizeBytes,
    commandId,
    receivedAt,
    at,
    queues,
    instanceId,
    hostname,
    version,
    connected,
    registered,
    heartbeat,
    _package,
    message,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
