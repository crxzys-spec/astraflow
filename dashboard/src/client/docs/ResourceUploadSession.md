# ResourceUploadSession


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**uploadId** | **string** |  | [default to undefined]
**filename** | **string** |  | [default to undefined]
**sizeBytes** | **number** |  | [default to undefined]
**mimeType** | **string** |  | [optional] [default to undefined]
**sha256** | **string** |  | [optional] [default to undefined]
**chunkSize** | **number** |  | [default to undefined]
**uploadedBytes** | **number** |  | [default to undefined]
**nextPart** | **number** |  | [default to undefined]
**totalParts** | **number** |  | [default to undefined]
**completedParts** | **Array&lt;number&gt;** |  | [optional] [default to undefined]
**status** | **string** |  | [default to undefined]
**resourceId** | **string** |  | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**createdAt** | **string** |  | [default to undefined]
**updatedAt** | **string** |  | [default to undefined]

## Example

```typescript
import { ResourceUploadSession } from './api';

const instance: ResourceUploadSession = {
    uploadId,
    filename,
    sizeBytes,
    mimeType,
    sha256,
    chunkSize,
    uploadedBytes,
    nextPart,
    totalParts,
    completedParts,
    status,
    resourceId,
    metadata,
    createdAt,
    updatedAt,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
