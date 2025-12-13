# CatalogNode


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **string** |  | [default to undefined]
**label** | **string** |  | [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**role** | **string** |  | [optional] [default to undefined]
**category** | **string** |  | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**status** | **string** |  | [optional] [default to undefined]
**packageName** | **string** |  | [default to undefined]
**defaultVersion** | **string** |  | [optional] [default to undefined]
**latestVersion** | **string** |  | [optional] [default to undefined]
**versions** | [**Array&lt;CatalogNodeVersion&gt;**](CatalogNodeVersion.md) |  | [default to undefined]

## Example

```typescript
import { CatalogNode } from './api';

const instance: CatalogNode = {
    type,
    label,
    description,
    role,
    category,
    tags,
    status,
    packageName,
    defaultVersion,
    latestVersion,
    versions,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
