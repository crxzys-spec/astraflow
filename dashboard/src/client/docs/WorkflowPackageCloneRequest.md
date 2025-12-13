# WorkflowPackageCloneRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**versionId** | **string** | Explicit version id to clone; defaults to the latest. | [optional] [default to undefined]
**version** | **string** | Version string to clone when versionId is omitted. | [optional] [default to undefined]
**workflowName** | **string** | Optional override for the cloned workflow name. | [optional] [default to undefined]

## Example

```typescript
import { WorkflowPackageCloneRequest } from './api';

const instance: WorkflowPackageCloneRequest = {
    versionId,
    version,
    workflowName,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
