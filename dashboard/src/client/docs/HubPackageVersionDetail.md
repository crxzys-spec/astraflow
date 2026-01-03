# HubPackageVersionDetail


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** |  | [default to undefined]
**version** | **string** |  | [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**readme** | **string** |  | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**distTags** | **{ [key: string]: string; }** |  | [optional] [default to undefined]
**archiveSha256** | **string** |  | [optional] [default to undefined]
**archiveSizeBytes** | **number** |  | [optional] [default to undefined]
**ownerId** | **string** |  | [optional] [default to undefined]
**ownerName** | **string** |  | [optional] [default to undefined]
**visibility** | [**HubVisibility**](HubVisibility.md) |  | [optional] [default to undefined]
**publishedAt** | **string** |  | [optional] [default to undefined]
**updatedAt** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { HubPackageVersionDetail } from './api';

const instance: HubPackageVersionDetail = {
    name,
    version,
    description,
    readme,
    tags,
    distTags,
    archiveSha256,
    archiveSizeBytes,
    ownerId,
    ownerName,
    visibility,
    publishedAt,
    updatedAt,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
