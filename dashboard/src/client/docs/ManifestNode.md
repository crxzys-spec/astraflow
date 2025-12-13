# ManifestNode


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **string** |  | [default to undefined]
**role** | **string** | Execution role of the node. | [optional] [default to undefined]
**status** | **string** |  | [default to undefined]
**category** | **string** |  | [default to undefined]
**label** | **string** |  | [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**tags** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**adapter** | **string** |  | [default to undefined]
**handler** | **string** |  | [default to undefined]
**config** | **{ [key: string]: any; }** | Optional static configuration forwarded to the handler. | [optional] [default to undefined]
**schema** | [**ManifestNodeSchema**](ManifestNodeSchema.md) |  | [default to undefined]
**ui** | [**ManifestNodeUI**](ManifestNodeUI.md) |  | [optional] [default to undefined]

## Example

```typescript
import { ManifestNode } from './api';

const instance: ManifestNode = {
    type,
    role,
    status,
    category,
    label,
    description,
    tags,
    adapter,
    handler,
    config,
    schema,
    ui,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
