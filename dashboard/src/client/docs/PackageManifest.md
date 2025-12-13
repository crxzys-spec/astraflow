# PackageManifest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schemaVersion** | **string** | Manifest schema version (semver). | [default to undefined]
**name** | **string** | Package identifier (lowercase with dots/underscores). | [default to undefined]
**version** | **string** | Package version in semver format. | [default to undefined]
**description** | **string** | Short summary of the package. | [default to undefined]
**adapters** | [**Array&lt;ManifestAdapter&gt;**](ManifestAdapter.md) |  | [default to undefined]
**python** | [**ManifestPythonConfig**](ManifestPythonConfig.md) |  | [default to undefined]
**nodes** | [**Array&lt;ManifestNode&gt;**](ManifestNode.md) |  | [default to undefined]
**resources** | [**Array&lt;ManifestResource&gt;**](ManifestResource.md) |  | [optional] [default to undefined]
**hooks** | [**ManifestHooks**](ManifestHooks.md) |  | [optional] [default to undefined]
**signature** | [**ManifestSignature**](ManifestSignature.md) |  | [optional] [default to undefined]

## Example

```typescript
import { PackageManifest } from './api';

const instance: PackageManifest = {
    schemaVersion,
    name,
    version,
    description,
    adapters,
    python,
    nodes,
    resources,
    hooks,
    signature,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
