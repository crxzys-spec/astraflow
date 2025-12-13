# RunMetricsEvent


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**runId** | **string** |  | [default to undefined]
**metric** | **string** |  | [default to undefined]
**value** | **number** |  | [default to undefined]
**tags** | **{ [key: string]: string; }** |  | [optional] [default to undefined]

## Example

```typescript
import { RunMetricsEvent } from './api';

const instance: RunMetricsEvent = {
    kind,
    runId,
    metric,
    value,
    tags,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
