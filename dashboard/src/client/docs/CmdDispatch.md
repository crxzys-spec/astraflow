# CmdDispatch


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**runId** | **string** |  | [default to undefined]
**nodeId** | **string** |  | [default to undefined]
**definitionHash** | **string** |  | [default to undefined]
**trace** | [**TraceContext**](TraceContext.md) |  | [default to undefined]
**payload** | **{ [key: string]: any; }** |  | [optional] [default to undefined]

## Example

```typescript
import { CmdDispatch } from './api';

const instance: CmdDispatch = {
    kind,
    runId,
    nodeId,
    definitionHash,
    trace,
    payload,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
