# ManifestBinding


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**path** | **string** |  | [default to undefined]
**mode** | **string** |  | [optional] [default to undefined]
**prefix** | **string** | Optional textual prefix (e.g. \&#39;@workflowA.subgraphB.#nodeY\&#39;) applied before resolving the JSON pointer. | [optional] [default to undefined]
**scope** | [**BindingScope**](BindingScope.md) |  | [optional] [default to undefined]

## Example

```typescript
import { ManifestBinding } from './api';

const instance: ManifestBinding = {
    path,
    mode,
    prefix,
    scope,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
