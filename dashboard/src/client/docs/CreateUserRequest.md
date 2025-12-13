# CreateUserRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**username** | **string** |  | [default to undefined]
**displayName** | **string** |  | [default to undefined]
**password** | **string** |  | [default to undefined]
**roles** | **Array&lt;string&gt;** | Optional initial roles to assign to the user. | [optional] [default to undefined]

## Example

```typescript
import { CreateUserRequest } from './api';

const instance: CreateUserRequest = {
    username,
    displayName,
    password,
    roles,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
