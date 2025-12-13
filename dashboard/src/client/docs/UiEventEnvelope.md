# UiEventEnvelope


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **string** |  | [default to undefined]
**id** | **string** |  | [default to undefined]
**type** | [**UiEventType**](UiEventType.md) |  | [default to undefined]
**occurredAt** | **string** |  | [default to undefined]
**scope** | [**UiEventScope**](UiEventScope.md) |  | [default to undefined]
**replayed** | **boolean** |  | [optional] [default to undefined]
**correlationId** | **string** |  | [optional] [default to undefined]
**meta** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**data** | [**UiEventPayload**](UiEventPayload.md) |  | [default to undefined]

## Example

```typescript
import { UiEventEnvelope } from './api';

const instance: UiEventEnvelope = {
    version,
    id,
    type,
    occurredAt,
    scope,
    replayed,
    correlationId,
    meta,
    data,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
