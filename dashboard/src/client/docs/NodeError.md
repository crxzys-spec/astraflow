# NodeError


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**runId** | **string** |  | [default to undefined]
**nodeId** | **string** |  | [default to undefined]
**definitionHash** | **string** |  | [default to undefined]
**error** | [**ResultError**](ResultError.md) |  | [default to undefined]
**metadata** | [**NodeErrorMetadata**](NodeErrorMetadata.md) |  | [optional] [default to undefined]

## Example

```typescript
import { NodeError } from './api';

const instance: NodeError = {
    kind,
    runId,
    nodeId,
    definitionHash,
    error,
    metadata,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
