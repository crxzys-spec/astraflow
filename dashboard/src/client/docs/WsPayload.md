# WsPayload


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**runId** | **string** |  | [default to undefined]
**nodeId** | **string** |  | [default to undefined]
**definitionHash** | **string** |  | [default to undefined]
**trace** | [**TraceContext**](TraceContext.md) |  | [default to undefined]
**payload** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**status** | **string** |  | [default to undefined]
**outputs** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**metadata** | [**NodeErrorMetadata**](NodeErrorMetadata.md) |  | [optional] [default to undefined]
**error** | [**ResultError**](ResultError.md) |  | [default to undefined]
**workerId** | **string** |  | [optional] [default to undefined]
**at** | **string** |  | [optional] [default to undefined]
**queues** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**name** | **string** |  | [optional] [default to undefined]
**version** | **string** |  | [optional] [default to undefined]
**message** | **string** |  | [optional] [default to undefined]
**commandId** | **string** |  | [optional] [default to undefined]
**receivedAt** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { WsPayload } from './api';

const instance: WsPayload = {
    kind,
    runId,
    nodeId,
    definitionHash,
    trace,
    payload,
    status,
    outputs,
    metadata,
    error,
    workerId,
    at,
    queues,
    name,
    version,
    message,
    commandId,
    receivedAt,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
