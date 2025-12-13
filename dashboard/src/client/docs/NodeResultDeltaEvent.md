# NodeResultDeltaEvent


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**runId** | **string** |  | [default to undefined]
**nodeId** | **string** |  | [default to undefined]
**revision** | **number** |  | [default to undefined]
**sequence** | **number** |  | [default to undefined]
**operation** | **string** |  | [default to undefined]
**path** | **string** |  | [optional] [default to undefined]
**payload** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**patches** | [**Array&lt;JsonPatchOperation&gt;**](JsonPatchOperation.md) |  | [optional] [default to undefined]
**chunkMeta** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**terminal** | **boolean** |  | [optional] [default to false]

## Example

```typescript
import { NodeResultDeltaEvent } from './api';

const instance: NodeResultDeltaEvent = {
    kind,
    runId,
    nodeId,
    revision,
    sequence,
    operation,
    path,
    payload,
    patches,
    chunkMeta,
    terminal,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
