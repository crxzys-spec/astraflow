# HubWorkflowVersionDetail


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [default to undefined]
**version** | **string** |  | [default to undefined]
**summary** | **string** |  | [optional] [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**previewImage** | **string** |  | [optional] [default to undefined]
**dependencies** | [**Array&lt;HubPackageDependency&gt;**](HubPackageDependency.md) |  | [optional] [default to undefined]
**publishedAt** | **string** |  | [optional] [default to undefined]
**publisherId** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { HubWorkflowVersionDetail } from './api';

const instance: HubWorkflowVersionDetail = {
    id,
    version,
    summary,
    description,
    tags,
    previewImage,
    dependencies,
    publishedAt,
    publisherId,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
