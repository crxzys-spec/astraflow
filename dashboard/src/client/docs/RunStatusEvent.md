# RunStatusEvent


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**runId** | **string** |  | [default to undefined]
**status** | [**RunStatus**](RunStatus.md) |  | [default to undefined]
**startedAt** | **string** |  | [optional] [default to undefined]
**finishedAt** | **string** |  | [optional] [default to undefined]
**reason** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { RunStatusEvent } from './api';

const instance: RunStatusEvent = {
    kind,
    runId,
    status,
    startedAt,
    finishedAt,
    reason,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
