# WorkerHeartbeatEvent


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**workerName** | **string** |  | [default to undefined]
**at** | **string** |  | [default to undefined]
**queues** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**instanceId** | **string** |  | [optional] [default to undefined]
**hostname** | **string** |  | [optional] [default to undefined]
**version** | **string** |  | [optional] [default to undefined]
**connected** | **boolean** |  | [optional] [default to undefined]
**registered** | **boolean** |  | [optional] [default to undefined]
**heartbeat** | [**WorkerHeartbeatSnapshot**](WorkerHeartbeatSnapshot.md) |  | [optional] [default to undefined]

## Example

```typescript
import { WorkerHeartbeatEvent } from './api';

const instance: WorkerHeartbeatEvent = {
    kind,
    workerName,
    at,
    queues,
    instanceId,
    hostname,
    version,
    connected,
    registered,
    heartbeat,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
