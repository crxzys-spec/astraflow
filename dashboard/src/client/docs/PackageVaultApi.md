# PackageVaultApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**deletePackageVaultItem**](#deletepackagevaultitem) | **DELETE** /api/v1/package-vault/{packageName}/{key} | Delete package vault entry|
|[**listPackageVault**](#listpackagevault) | **GET** /api/v1/package-vault | List package vault entries|
|[**upsertPackageVault**](#upsertpackagevault) | **PUT** /api/v1/package-vault | Upsert package vault entries|

# **deletePackageVaultItem**
> deletePackageVaultItem()


### Example

```typescript
import {
    PackageVaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PackageVaultApi(configuration);

let packageName: string; // (default to undefined)
let key: string; // (default to undefined)

const { status, data } = await apiInstance.deletePackageVaultItem(
    packageName,
    key
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageName** | [**string**] |  | defaults to undefined|
| **key** | [**string**] |  | defaults to undefined|


### Return type

void (empty response body)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**204** | Deleted |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **listPackageVault**
> PackageVaultList listPackageVault()


### Example

```typescript
import {
    PackageVaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PackageVaultApi(configuration);

let packageName: string; // (default to undefined)

const { status, data } = await apiInstance.listPackageVault(
    packageName
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageName** | [**string**] |  | defaults to undefined|


### Return type

**PackageVaultList**

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

# **upsertPackageVault**
> PackageVaultList upsertPackageVault(packageVaultUpsertRequest)


### Example

```typescript
import {
    PackageVaultApi,
    Configuration,
    PackageVaultUpsertRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new PackageVaultApi(configuration);

let packageVaultUpsertRequest: PackageVaultUpsertRequest; //

const { status, data } = await apiInstance.upsertPackageVault(
    packageVaultUpsertRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageVaultUpsertRequest** | **PackageVaultUpsertRequest**|  | |


### Return type

**PackageVaultList**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |
|**400** | Invalid input |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

