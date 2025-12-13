# CommandErrorEvent


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**commandId** | **string** |  | [default to undefined]
**workerId** | **string** |  | [default to undefined]
**error** | [**ResultError**](ResultError.md) |  | [default to undefined]

## Example

```typescript
import { CommandErrorEvent } from './api';

const instance: CommandErrorEvent = {
    kind,
    commandId,
    workerId,
    error,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
