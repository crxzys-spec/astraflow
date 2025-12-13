# NodeStatusEvent


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**runId** | **string** |  | [default to undefined]
**nodeId** | **string** |  | [default to undefined]
**status** | **string** |  | [default to undefined]
**workerId** | **string** |  | [optional] [default to undefined]
**seq** | **number** |  | [optional] [default to undefined]
**ackPending** | **boolean** |  | [optional] [default to undefined]

## Example

```typescript
import { NodeStatusEvent } from './api';

const instance: NodeStatusEvent = {
    kind,
    runId,
    nodeId,
    status,
    workerId,
    seq,
    ackPending,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
