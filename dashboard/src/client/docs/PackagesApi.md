# PackagesApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**getPackage**](#getpackage) | **GET** /api/v1/packages/{packageName} | Get package detail|
|[**listPackages**](#listpackages) | **GET** /api/v1/packages | List available packages|

# **getPackage**
> PackageDetail getPackage()


### Example

```typescript
import {
    PackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PackagesApi(configuration);

let packageName: string; // (default to undefined)
let version: string; //Specific package version to retrieve. Defaults to the latest available version. (optional) (default to undefined)

const { status, data } = await apiInstance.getPackage(
    packageName,
    version
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageName** | [**string**] |  | defaults to undefined|
| **version** | [**string**] | Specific package version to retrieve. Defaults to the latest available version. | (optional) defaults to undefined|


### Return type

**PackageDetail**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **listPackages**
> PackageList listPackages()


### Example

```typescript
import {
    PackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PackagesApi(configuration);

const { status, data } = await apiInstance.listPackages();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**PackageList**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

