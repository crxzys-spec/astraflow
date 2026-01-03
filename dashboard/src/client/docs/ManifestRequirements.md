# ManifestRequirements


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**resources** | [**Array&lt;ManifestResourceRequirement&gt;**](ManifestResourceRequirement.md) | Resource requirements declared by the package. Deprecated in favor of permissions/vault. | [optional] [default to undefined]
**permissions** | [**Array&lt;ManifestPermissionRequirement&gt;**](ManifestPermissionRequirement.md) | Package permissions requested to access user resources. | [optional] [default to undefined]
**vault** | [**Array&lt;ManifestVaultRequirement&gt;**](ManifestVaultRequirement.md) | Package-owned secret entries stored in the user\&#39;s vault. | [optional] [default to undefined]

## Example

```typescript
import { ManifestRequirements } from './api';

const instance: ManifestRequirements = {
    resources,
    permissions,
    vault,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
