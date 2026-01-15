# HubAccountApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**getHubAccount**](#gethubaccount) | **GET** /api/v1/hub/account | Get hub account profile via scheduler proxy|

# **getHubAccount**
> HubAccount getHubAccount()


### Example

```typescript
import {
    HubAccountApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new HubAccountApi(configuration);

const { status, data } = await apiInstance.getHubAccount();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**HubAccount**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |
|**400** | Invalid input |  -  |
|**401** | Authentication required or credentials invalid |  -  |
|**403** | Authenticated but lacks required permissions |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

