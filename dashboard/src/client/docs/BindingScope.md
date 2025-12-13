# BindingScope

Canonical representation of a binding prefix used to resolve nodes across workflows or subgraphs.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **string** | local &#x3D; default workflow, subgraph &#x3D; inline subgraph alias chain. | [optional] [default to undefined]
**subgraphAliases** | **Array&lt;string&gt;** | Ordered list of inline subgraph aliases traversed to reach the node. | [optional] [default to undefined]
**nodeId** | **string** | Explicit node identifier within the resolved scope (used for \&#39;#nodeId\&#39; prefixes or workflow-level references). | [optional] [default to undefined]
**prefix** | **string** | Raw prefix string captured before parsing (mirrors UIBinding.prefix for auditing/backwards compatibility). | [optional] [default to undefined]

## Example

```typescript
import { BindingScope } from './api';

const instance: BindingScope = {
    kind,
    subgraphAliases,
    nodeId,
    prefix,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
