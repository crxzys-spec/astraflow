# PackagePermissionsApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**createPackagePermission**](#createpackagepermission) | **POST** /api/v1/package-permissions | Grant package permissions|
|[**deletePackagePermission**](#deletepackagepermission) | **DELETE** /api/v1/package-permissions/{permissionId} | Revoke package permission|
|[**listPackagePermissions**](#listpackagepermissions) | **GET** /api/v1/package-permissions | List package permissions|

# **createPackagePermission**
> PackagePermission createPackagePermission(packagePermissionCreateRequest)


### Example

```typescript
import {
    PackagePermissionsApi,
    Configuration,
    PackagePermissionCreateRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new PackagePermissionsApi(configuration);

let packagePermissionCreateRequest: PackagePermissionCreateRequest; //

const { status, data } = await apiInstance.createPackagePermission(
    packagePermissionCreateRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packagePermissionCreateRequest** | **PackagePermissionCreateRequest**|  | |


### Return type

**PackagePermission**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Created |  -  |
|**400** | Invalid input |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **deletePackagePermission**
> deletePackagePermission()


### Example

```typescript
import {
    PackagePermissionsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PackagePermissionsApi(configuration);

let permissionId: string; // (default to undefined)

const { status, data } = await apiInstance.deletePackagePermission(
    permissionId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **permissionId** | [**string**] |  | defaults to undefined|


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

# **listPackagePermissions**
> PackagePermissionList listPackagePermissions()


### Example

```typescript
import {
    PackagePermissionsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PackagePermissionsApi(configuration);

let packageName: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.listPackagePermissions(
    packageName
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageName** | [**string**] |  | (optional) defaults to undefined|


### Return type

**PackagePermissionList**

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

