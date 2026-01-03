# RegistryWorkflowImportRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**packageId** | **string** | Registry workflow package id. | [default to undefined]
**versionId** | **string** | Specific registry version id to import. | [optional] [default to undefined]
**version** | **string** | Version string to import when versionId is omitted. | [optional] [default to undefined]
**name** | **string** | Optional override for the imported workflow name. | [optional] [default to undefined]

## Example

```typescript
import { RegistryWorkflowImportRequest } from './api';

const instance: RegistryWorkflowImportRequest = {
    packageId,
    versionId,
    version,
    name,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
