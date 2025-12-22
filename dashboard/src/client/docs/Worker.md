# Worker


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [default to undefined]
**hostname** | **string** |  | [optional] [default to undefined]
**lastHeartbeatAt** | **string** |  | [default to undefined]
**queues** | **Array&lt;string&gt;** |  | [default to undefined]
**packages** | [**Array&lt;WorkerPackage&gt;**](WorkerPackage.md) |  | [optional] [default to undefined]
**meta** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**connected** | **boolean** |  | [optional] [default to undefined]
**registered** | **boolean** |  | [optional] [default to undefined]
**tenant** | **string** |  | [optional] [default to undefined]
**instanceId** | **string** |  | [optional] [default to undefined]
**version** | **string** |  | [optional] [default to undefined]
**capabilities** | [**WorkerCapabilities**](WorkerCapabilities.md) |  | [optional] [default to undefined]
**payloadTypes** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**heartbeat** | [**WorkerHeartbeatSnapshot**](WorkerHeartbeatSnapshot.md) |  | [optional] [default to undefined]

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
    connected,
    registered,
    tenant,
    instanceId,
    version,
    capabilities,
    payloadTypes,
    heartbeat,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
