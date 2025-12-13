# RunSnapshotEvent


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**run** | [**Run**](Run.md) |  | [default to undefined]
**nodes** | [**Array&lt;RunNodeStatus&gt;**](RunNodeStatus.md) |  | [optional] [default to undefined]

## Example

```typescript
import { RunSnapshotEvent } from './api';

const instance: RunSnapshotEvent = {
    kind,
    run,
    nodes,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
