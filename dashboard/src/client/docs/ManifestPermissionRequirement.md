# ManifestPermissionRequirement


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**key** | **string** | Stable permission identifier used for grants. | [default to undefined]
**types** | **Array&lt;string&gt;** | Resource types covered by this permission (file, image, audio, video, kv, secret, etc.). | [default to undefined]
**providers** | **Array&lt;string&gt;** | Optional storage providers this permission applies to. | [optional] [default to undefined]
**actions** | **Array&lt;string&gt;** | Allowed actions for the permission (read, write, use). | [optional] [default to undefined]
**required** | **boolean** | Whether the permission must be granted before execution. | [optional] [default to true]
**description** | **string** | Human-readable explanation of why the permission is needed. | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** | Additional permission metadata. | [optional] [default to undefined]

## Example

```typescript
import { ManifestPermissionRequirement } from './api';

const instance: ManifestPermissionRequirement = {
    key,
    types,
    providers,
    actions,
    required,
    description,
    metadata,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
