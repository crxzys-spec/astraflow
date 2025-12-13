# NodeResultSnapshotEvent


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**runId** | **string** |  | [default to undefined]
**nodeId** | **string** |  | [default to undefined]
**revision** | **number** |  | [default to undefined]
**format** | **string** |  | [optional] [default to FormatEnum_Json]
**content** | **{ [key: string]: any; }** |  | [default to undefined]
**artifacts** | [**Array&lt;RunArtifact&gt;**](RunArtifact.md) |  | [optional] [default to undefined]
**summary** | **string** |  | [optional] [default to undefined]
**complete** | **boolean** |  | [optional] [default to false]

## Example

```typescript
import { NodeResultSnapshotEvent } from './api';

const instance: NodeResultSnapshotEvent = {
    kind,
    runId,
    nodeId,
    revision,
    format,
    content,
    artifacts,
    summary,
    complete,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
