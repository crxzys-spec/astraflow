# NodeResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**runId** | **string** |  | [default to undefined]
**nodeId** | **string** |  | [default to undefined]
**status** | **string** |  | [default to undefined]
**definitionHash** | **string** |  | [default to undefined]
**outputs** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**metadata** | [**NodeResultMetadata**](NodeResultMetadata.md) |  | [optional] [default to undefined]

## Example

```typescript
import { NodeResult } from './api';

const instance: NodeResult = {
    kind,
    runId,
    nodeId,
    status,
    definitionHash,
    outputs,
    metadata,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
