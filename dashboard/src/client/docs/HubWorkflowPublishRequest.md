# HubWorkflowPublishRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**workflowId** | **string** |  | [optional] [default to undefined]
**name** | **string** |  | [default to undefined]
**version** | **string** |  | [default to undefined]
**summary** | **string** |  | [optional] [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**visibility** | [**HubVisibility**](HubVisibility.md) |  | [optional] [default to undefined]
**previewImage** | **string** |  | [optional] [default to undefined]
**dependencies** | [**Array&lt;HubPackageDependency&gt;**](HubPackageDependency.md) |  | [optional] [default to undefined]
**definition** | **{ [key: string]: any; }** |  | [default to undefined]

## Example

```typescript
import { HubWorkflowPublishRequest } from './api';

const instance: HubWorkflowPublishRequest = {
    workflowId,
    name,
    version,
    summary,
    description,
    tags,
    visibility,
    previewImage,
    dependencies,
    definition,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
