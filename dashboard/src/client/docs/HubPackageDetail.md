# HubPackageDetail


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** |  | [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**readme** | **string** |  | [optional] [default to undefined]
**versions** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**distTags** | **{ [key: string]: string; }** |  | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**ownerId** | **string** |  | [optional] [default to undefined]
**ownerName** | **string** |  | [optional] [default to undefined]
**updatedAt** | **string** |  | [optional] [default to undefined]
**visibility** | [**HubVisibility**](HubVisibility.md) |  | [optional] [default to undefined]

## Example

```typescript
import { HubPackageDetail } from './api';

const instance: HubPackageDetail = {
    name,
    description,
    readme,
    versions,
    distTags,
    tags,
    ownerId,
    ownerName,
    updatedAt,
    visibility,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
