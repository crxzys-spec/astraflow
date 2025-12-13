# WorkflowPackageVersion


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [default to undefined]
**version** | **string** |  | [default to undefined]
**changelog** | **string** |  | [optional] [default to undefined]
**publishedAt** | **string** |  | [default to undefined]
**publisherId** | **string** |  | [optional] [default to undefined]
**previewImage** | **string** | Base64-encoded preview of the workflow canvas for this version. | [optional] [default to undefined]

## Example

```typescript
import { WorkflowPackageVersion } from './api';

const instance: WorkflowPackageVersion = {
    id,
    version,
    changelog,
    publishedAt,
    publisherId,
    previewImage,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
