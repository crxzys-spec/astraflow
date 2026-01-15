# HubLocalPackagePublishRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** |  | [default to undefined]
**version** | **string** | Optional package version; defaults to latest local version. | [optional] [default to undefined]
**visibility** | [**HubVisibility**](HubVisibility.md) |  | [optional] [default to undefined]
**summary** | **string** |  | [optional] [default to undefined]
**readme** | **string** |  | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** |  | [optional] [default to undefined]

## Example

```typescript
import { HubLocalPackagePublishRequest } from './api';

const instance: HubLocalPackagePublishRequest = {
    name,
    version,
    visibility,
    summary,
    readme,
    tags,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
