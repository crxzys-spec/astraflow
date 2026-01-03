# ManifestVaultRequirement


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**key** | **string** | Stable key used to store and retrieve the vault value. | [default to undefined]
**label** | **string** | Display label for the vault entry. | [optional] [default to undefined]
**type** | **string** | Vault value type (secret, string, json). | [default to undefined]
**required** | **boolean** | Whether the vault entry must be provided before execution. | [optional] [default to true]
**description** | **string** | Human-readable explanation of the vault entry. | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** | Additional vault metadata. | [optional] [default to undefined]

## Example

```typescript
import { ManifestVaultRequirement } from './api';

const instance: ManifestVaultRequirement = {
    key,
    label,
    type,
    required,
    description,
    metadata,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
