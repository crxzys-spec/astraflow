# Resource


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**resourceId** | **string** |  | [default to undefined]
**provider** | **string** |  | [default to undefined]
**type** | **string** |  | [default to undefined]
**filename** | **string** |  | [default to undefined]
**ownerId** | **string** |  | [optional] [default to undefined]
**visibility** | [**ResourceVisibility**](ResourceVisibility.md) |  | [optional] [default to undefined]
**mimeType** | **string** |  | [optional] [default to undefined]
**sizeBytes** | **number** |  | [default to undefined]
**sha256** | **string** |  | [optional] [default to undefined]
**createdAt** | **string** |  | [default to undefined]
**expiresAt** | **string** |  | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**downloadUrl** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { Resource } from './api';

const instance: Resource = {
    resourceId,
    provider,
    type,
    filename,
    ownerId,
    visibility,
    mimeType,
    sizeBytes,
    sha256,
    createdAt,
    expiresAt,
    metadata,
    downloadUrl,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
