# PackageSummary


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** |  | [default to undefined]
**description** | [**LocalizedText**](LocalizedText.md) |  | [optional] [default to undefined]
**latestVersion** | **string** |  | [optional] [default to undefined]
**defaultVersion** | **string** |  | [optional] [default to undefined]
**versions** | **Array&lt;string&gt;** |  | [default to undefined]
**ownerId** | **string** |  | [optional] [default to undefined]
**hub** | [**PackageHubMeta**](PackageHubMeta.md) |  | [optional] [default to undefined]
**hubVersions** | **Array&lt;string&gt;** |  | [optional] [default to undefined]

## Example

```typescript
import { PackageSummary } from './api';

const instance: PackageSummary = {
    name,
    description,
    latestVersion,
    defaultVersion,
    versions,
    ownerId,
    hub,
    hubVersions,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
