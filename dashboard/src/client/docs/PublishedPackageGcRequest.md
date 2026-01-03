# PublishedPackageGcRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**packageName** | **string** | Limit garbage collection to a specific package. | [optional] [default to undefined]
**maxVersions** | **number** | Override the max versions to keep per package. | [optional] [default to undefined]
**dryRun** | **boolean** | When true, report the versions that would be removed without deleting them. | [optional] [default to undefined]

## Example

```typescript
import { PublishedPackageGcRequest } from './api';

const instance: PublishedPackageGcRequest = {
    packageName,
    maxVersions,
    dryRun,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
