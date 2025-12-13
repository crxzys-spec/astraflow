# WorkerHeartbeatEvent


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**workerId** | **string** |  | [default to undefined]
**at** | **string** |  | [default to undefined]
**queues** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**capacity** | **{ [key: string]: any; }** |  | [optional] [default to undefined]

## Example

```typescript
import { WorkerHeartbeatEvent } from './api';

const instance: WorkerHeartbeatEvent = {
    kind,
    workerId,
    at,
    queues,
    capacity,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
