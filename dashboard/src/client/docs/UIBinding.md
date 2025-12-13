# UIBinding


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**path** | **string** | e.g. parameters.url / results.status | [default to undefined]
**mode** | **string** |  | [default to undefined]
**prefix** | **string** | Optional textual prefix (e.g. \&#39;@welcomeJourney.stage2.#notifyCustomer\&#39;) that scopes the binding before the JSON pointer root. | [optional] [default to undefined]
**scope** | [**BindingScope**](BindingScope.md) |  | [optional] [default to undefined]

## Example

```typescript
import { UIBinding } from './api';

const instance: UIBinding = {
    path,
    mode,
    prefix,
    scope,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
