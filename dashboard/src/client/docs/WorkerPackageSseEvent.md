# WorkerPackageSseEvent


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** |  | [default to undefined]
**workerName** | **string** |  | [default to undefined]
**_package** | **string** |  | [default to undefined]
**version** | **string** |  | [optional] [default to undefined]
**status** | [**WorkerPackageStatus**](WorkerPackageStatus.md) |  | [default to undefined]
**message** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { WorkerPackageSseEvent } from './api';

const instance: WorkerPackageSseEvent = {
    kind,
    workerName,
    _package,
    version,
    status,
    message,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
