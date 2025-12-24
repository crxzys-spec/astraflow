# ResourceUploadInitRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**filename** | **string** |  | [default to undefined]
**sizeBytes** | **number** |  | [default to undefined]
**provider** | **string** |  | [optional] [default to undefined]
**mimeType** | **string** |  | [optional] [default to undefined]
**sha256** | **string** |  | [optional] [default to undefined]
**chunkSize** | **number** |  | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** |  | [optional] [default to undefined]

## Example

```typescript
import { ResourceUploadInitRequest } from './api';

const instance: ResourceUploadInitRequest = {
    filename,
    sizeBytes,
    provider,
    mimeType,
    sha256,
    chunkSize,
    metadata,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
