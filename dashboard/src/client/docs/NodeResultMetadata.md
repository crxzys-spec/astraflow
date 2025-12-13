# NodeResultMetadata


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**error** | [**ResultError**](ResultError.md) |  | [optional] [default to undefined]
**lease** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**trace** | [**TraceContext**](TraceContext.md) |  | [optional] [default to undefined]

## Example

```typescript
import { NodeResultMetadata } from './api';

const instance: NodeResultMetadata = {
    error,
    lease,
    trace,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
