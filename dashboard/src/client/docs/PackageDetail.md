# PackageDetail


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** |  | [default to undefined]
**version** | **string** |  | [default to undefined]
**availableVersions** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**manifest** | [**PackageManifest**](PackageManifest.md) |  | [default to undefined]
**status** | [**PackageVersionStatus**](PackageVersionStatus.md) |  | [optional] [default to undefined]
**distTags** | **{ [key: string]: string; }** |  | [optional] [default to undefined]
**archiveSha256** | **string** |  | [optional] [default to undefined]
**archiveSizeBytes** | **number** |  | [optional] [default to undefined]
**ownerId** | **string** |  | [optional] [default to undefined]
**visibility** | [**PublishedPackageVisibility**](PublishedPackageVisibility.md) |  | [optional] [default to undefined]
**state** | [**PublishedPackageState**](PublishedPackageState.md) |  | [optional] [default to undefined]

## Example

```typescript
import { PackageDetail } from './api';

const instance: PackageDetail = {
    name,
    version,
    availableVersions,
    manifest,
    status,
    distTags,
    archiveSha256,
    archiveSizeBytes,
    ownerId,
    visibility,
    state,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
