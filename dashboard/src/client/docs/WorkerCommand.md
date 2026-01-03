# WorkerCommand


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **string** |  | [default to undefined]
**queue** | **string** |  | [default to undefined]
**name** | **string** |  | [default to undefined]
**version** | **string** |  | [optional] [default to undefined]
**url** | **string** | Optional archive URL; defaults to the published package archive. | [optional] [default to undefined]
**sha256** | **string** | Optional SHA-256 checksum of the archive. | [optional] [default to undefined]

## Example

```typescript
import { WorkerCommand } from './api';

const instance: WorkerCommand = {
    type,
    queue,
    name,
    version,
    url,
    sha256,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
