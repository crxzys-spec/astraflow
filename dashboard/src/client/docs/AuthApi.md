# AuthApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**authLogin**](#authlogin) | **POST** /api/v1/auth/login | Exchange username/password for a JWT|

# **authLogin**
> AuthLoginResponse authLogin(authLoginRequest)


### Example

```typescript
import {
    AuthApi,
    Configuration,
    AuthLoginRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AuthApi(configuration);

let authLoginRequest: AuthLoginRequest; //

const { status, data } = await apiInstance.authLogin(
    authLoginRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **authLoginRequest** | **AuthLoginRequest**|  | |


### Return type

**AuthLoginResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Authenticated |  -  |
|**401** | Authentication required or credentials invalid |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

