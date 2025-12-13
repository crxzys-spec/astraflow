# TraceContext


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**traceId** | **string** |  | [default to undefined]
**spanId** | **string** |  | [default to undefined]
**parentSpanId** | **string** |  | [optional] [default to undefined]
**baggage** | **{ [key: string]: string; }** |  | [optional] [default to undefined]

## Example

```typescript
import { TraceContext } from './api';

const instance: TraceContext = {
    traceId,
    spanId,
    parentSpanId,
    baggage,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
