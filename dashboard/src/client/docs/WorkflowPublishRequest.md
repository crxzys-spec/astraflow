# WorkflowPublishRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**packageId** | **string** | Existing package id to append a version to. | [optional] [default to undefined]
**slug** | **string** | Slug used when creating a new package. | [optional] [default to undefined]
**displayName** | **string** |  | [optional] [default to undefined]
**summary** | **string** |  | [optional] [default to undefined]
**visibility** | **string** | Desired visibility (private/internal/public). | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**version** | **string** | Semantic version for the published snapshot. | [default to undefined]
**changelog** | **string** |  | [optional] [default to undefined]
**previewImage** | **string** | Base64-encoded preview captured from the workflow canvas. | [optional] [default to undefined]

## Example

```typescript
import { WorkflowPublishRequest } from './api';

const instance: WorkflowPublishRequest = {
    packageId,
    slug,
    displayName,
    summary,
    visibility,
    tags,
    version,
    changelog,
    previewImage,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
