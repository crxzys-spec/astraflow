# CommandError


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [optional] [default to undefined]
**commandId** | **string** |  | [optional] [default to undefined]
**workerName** | **string** |  | [optional] [default to undefined]
**error** | [**ResultError**](ResultError.md) |  | [optional] [default to undefined]

## Example

```typescript
import { CommandError } from './api';

const instance: CommandError = {
    kind,
    commandId,
    workerName,
    error,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
