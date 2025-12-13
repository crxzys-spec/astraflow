# JsonPatchOperation


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**op** | **string** |  | [default to undefined]
**path** | **string** | JSON Pointer path. | [default to undefined]
**from** | **string** | Source path (for move/copy). | [optional] [default to undefined]
**value** | **any** | Value payload for add/replace/test. | [optional] [default to undefined]

## Example

```typescript
import { JsonPatchOperation } from './api';

const instance: JsonPatchOperation = {
    op,
    path,
    from,
    value,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
