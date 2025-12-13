# AuthLoginResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**accessToken** | **string** |  | [default to undefined]
**tokenType** | **string** |  | [default to undefined]
**expiresIn** | **number** | Seconds until the access token expires. | [default to undefined]
**user** | [**UserSummary**](UserSummary.md) |  | [default to undefined]

## Example

```typescript
import { AuthLoginResponse } from './api';

const instance: AuthLoginResponse = {
    accessToken,
    tokenType,
    expiresIn,
    user,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
