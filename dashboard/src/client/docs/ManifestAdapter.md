# ManifestAdapter


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** |  | [default to undefined]
**entrypoint** | **string** |  | [default to undefined]
**capabilities** | **Array&lt;string&gt;** |  | [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**idempotency** | **string** |  | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** |  | [optional] [default to undefined]

## Example

```typescript
import { ManifestAdapter } from './api';

const instance: ManifestAdapter = {
    name,
    entrypoint,
    capabilities,
    description,
    idempotency,
    metadata,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
