# WorkflowPackageSummary


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [default to undefined]
**slug** | **string** |  | [default to undefined]
**displayName** | **string** |  | [default to undefined]
**summary** | **string** |  | [optional] [default to undefined]
**visibility** | **string** | Visibility policy (private/internal/public). | [default to undefined]
**tags** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**ownerId** | **string** |  | [optional] [default to undefined]
**ownerName** | **string** |  | [optional] [default to undefined]
**updatedAt** | **string** |  | [optional] [default to undefined]
**latestVersion** | [**WorkflowPackageVersion**](WorkflowPackageVersion.md) |  | [optional] [default to undefined]
**previewImage** | **string** | Base64-encoded preview from the latest version when available. | [optional] [default to undefined]

## Example

```typescript
import { WorkflowPackageSummary } from './api';

const instance: WorkflowPackageSummary = {
    id,
    slug,
    displayName,
    summary,
    visibility,
    tags,
    ownerId,
    ownerName,
    updatedAt,
    latestVersion,
    previewImage,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
