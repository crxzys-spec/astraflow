# HubWorkflowImportResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**workflowId** | **string** |  | [default to undefined]
**workflowSourceId** | **string** |  | [default to undefined]
**versionId** | **string** |  | [default to undefined]
**dependencies** | [**Array&lt;HubPackageDependency&gt;**](HubPackageDependency.md) |  | [optional] [default to undefined]
**pulledPackages** | [**Array&lt;HubPackageDependency&gt;**](HubPackageDependency.md) |  | [optional] [default to undefined]

## Example

```typescript
import { HubWorkflowImportResponse } from './api';

const instance: HubWorkflowImportResponse = {
    workflowId,
    workflowSourceId,
    versionId,
    dependencies,
    pulledPackages,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
