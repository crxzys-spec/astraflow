# RegistryWorkflowImportResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**workflowId** | **string** |  | [default to undefined]
**packageId** | **string** |  | [default to undefined]
**versionId** | **string** |  | [default to undefined]
**dependencies** | [**Array&lt;RegistryPackageDependency&gt;**](RegistryPackageDependency.md) |  | [default to undefined]
**pulledPackages** | [**Array&lt;RegistryPackageDependency&gt;**](RegistryPackageDependency.md) |  | [default to undefined]
**missingPackages** | [**Array&lt;RegistryPackageDependency&gt;**](RegistryPackageDependency.md) |  | [optional] [default to undefined]

## Example

```typescript
import { RegistryWorkflowImportResponse } from './api';

const instance: RegistryWorkflowImportResponse = {
    workflowId,
    packageId,
    versionId,
    dependencies,
    pulledPackages,
    missingPackages,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
