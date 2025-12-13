# Worker


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [default to undefined]
**hostname** | **string** |  | [optional] [default to undefined]
**lastHeartbeatAt** | **string** |  | [default to undefined]
**queues** | **Array&lt;string&gt;** |  | [default to undefined]
**packages** | [**Array&lt;WorkerPackagesInner&gt;**](WorkerPackagesInner.md) |  | [optional] [default to undefined]
**meta** | **{ [key: string]: any; }** |  | [optional] [default to undefined]

## Example

```typescript
import { Worker } from './api';

const instance: Worker = {
    id,
    hostname,
    lastHeartbeatAt,
    queues,
    packages,
    meta,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
