# WorkflowNodeState

Scheduler-owned runtime hints attached to a workflow node during builder playback or run overlays.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**stage** | **string** | Current scheduler-reported stage (e.g. idle, queued, running, completed, failed). | [optional] [default to undefined]
**progress** | **number** | Optional 0-1 normalized progress indicator. | [optional] [default to undefined]
**lastUpdatedAt** | **string** | ISO-8601 timestamp for the last state transition. | [optional] [default to undefined]
**message** | **string** | Human-friendly hint surfaced to the UI. | [optional] [default to undefined]
**error** | [**ResultError**](ResultError.md) |  | [optional] [default to undefined]

## Example

```typescript
import { WorkflowNodeState } from './api';

const instance: WorkflowNodeState = {
    stage,
    progress,
    lastUpdatedAt,
    message,
    error,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
