# Run


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**runId** | **string** |  | [default to undefined]
**status** | [**RunStatus**](RunStatus.md) |  | [default to undefined]
**definitionHash** | **string** |  | [default to undefined]
**clientId** | **string** |  | [default to undefined]
**startedAt** | **string** |  | [optional] [default to undefined]
**finishedAt** | **string** |  | [optional] [default to undefined]
**error** | [**ResultError**](ResultError.md) |  | [optional] [default to undefined]
**artifacts** | [**Array&lt;RunArtifact&gt;**](RunArtifact.md) |  | [optional] [default to undefined]
**nodes** | [**Array&lt;RunNodeStatus&gt;**](RunNodeStatus.md) |  | [optional] [default to undefined]

## Example

```typescript
import { Run } from './api';

const instance: Run = {
    runId,
    status,
    definitionHash,
    clientId,
    startedAt,
    finishedAt,
    error,
    artifacts,
    nodes,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
