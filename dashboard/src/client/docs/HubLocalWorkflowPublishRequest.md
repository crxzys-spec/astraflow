# HubLocalWorkflowPublishRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**workflowId** | **string** |  | [default to undefined]
**name** | **string** | Optional override for the workflow name. | [optional] [default to undefined]
**version** | **string** |  | [default to undefined]
**summary** | **string** |  | [optional] [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**visibility** | [**HubVisibility**](HubVisibility.md) |  | [optional] [default to undefined]
**previewImage** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { HubLocalWorkflowPublishRequest } from './api';

const instance: HubLocalWorkflowPublishRequest = {
    workflowId,
    name,
    version,
    summary,
    description,
    tags,
    visibility,
    previewImage,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
