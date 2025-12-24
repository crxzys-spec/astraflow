# ManifestResourceRequirement


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**key** | **string** |  | [default to undefined]
**type** | **string** |  | [default to undefined]
**actions** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**required** | **boolean** |  | [optional] [default to true]
**description** | **string** |  | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** |  | [optional] [default to undefined]

## Example

```typescript
import { ManifestResourceRequirement } from './api';

const instance: ManifestResourceRequirement = {
    key,
    type,
    actions,
    required,
    description,
    metadata,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
