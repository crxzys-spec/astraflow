# EventEnvelope


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | [**EventType**](EventType.md) |  | [default to undefined]
**ts** | **string** |  | [default to undefined]
**id** | **string** | Monotonic event id for resume | [default to undefined]
**tenant** | **string** |  | [optional] [default to undefined]
**payload** | [**WsPayload**](WsPayload.md) |  | [default to undefined]

## Example

```typescript
import { EventEnvelope } from './api';

const instance: EventEnvelope = {
    type,
    ts,
    id,
    tenant,
    payload,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
