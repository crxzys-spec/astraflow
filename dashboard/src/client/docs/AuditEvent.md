# AuditEvent


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**eventId** | **string** |  | [default to undefined]
**actorId** | **string** |  | [optional] [default to undefined]
**action** | **string** |  | [default to undefined]
**targetType** | **string** |  | [default to undefined]
**targetId** | **string** |  | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**createdAt** | **string** |  | [default to undefined]

## Example

```typescript
import { AuditEvent } from './api';

const instance: AuditEvent = {
    eventId,
    actorId,
    action,
    targetType,
    targetId,
    metadata,
    createdAt,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
