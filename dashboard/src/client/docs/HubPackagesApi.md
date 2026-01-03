# HubPackagesApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**downloadHubPackageArchive**](#downloadhubpackagearchive) | **GET** /api/v1/hub/packages/{packageName}/archive | Download hub package archive|
|[**getHubPackage**](#gethubpackage) | **GET** /api/v1/hub/packages/{packageName} | Get hub package detail|
|[**getHubPackageVersion**](#gethubpackageversion) | **GET** /api/v1/hub/packages/{packageName}/versions/{version} | Get hub package version detail|
|[**installHubPackage**](#installhubpackage) | **POST** /api/v1/hub/packages/{packageName}/install | Install hub package into the local catalog|
|[**listHubPackages**](#listhubpackages) | **GET** /api/v1/hub/packages | List hub packages|
|[**publishHubPackage**](#publishhubpackage) | **POST** /api/v1/hub/packages | Publish a package archive to Hub|

# **downloadHubPackageArchive**
> File downloadHubPackageArchive()


### Example

```typescript
import {
    HubPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new HubPackagesApi(configuration);

let packageName: string; // (default to undefined)
let version: string; //Optional version to download (optional) (default to undefined)

const { status, data } = await apiInstance.downloadHubPackageArchive(
    packageName,
    version
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageName** | [**string**] |  | defaults to undefined|
| **version** | [**string**] | Optional version to download | (optional) defaults to undefined|


### Return type

**File**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/zip, application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getHubPackage**
> HubPackageDetail getHubPackage()


### Example

```typescript
import {
    HubPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new HubPackagesApi(configuration);

let packageName: string; // (default to undefined)

const { status, data } = await apiInstance.getHubPackage(
    packageName
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageName** | [**string**] |  | defaults to undefined|


### Return type

**HubPackageDetail**

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

# **getHubPackageVersion**
> HubPackageVersionDetail getHubPackageVersion()


### Example

```typescript
import {
    HubPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new HubPackagesApi(configuration);

let packageName: string; // (default to undefined)
let version: string; // (default to undefined)

const { status, data } = await apiInstance.getHubPackageVersion(
    packageName,
    version
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageName** | [**string**] |  | defaults to undefined|
| **version** | [**string**] |  | defaults to undefined|


### Return type

**HubPackageVersionDetail**

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

# **installHubPackage**
> HubPackageInstallResponse installHubPackage()


### Example

```typescript
import {
    HubPackagesApi,
    Configuration,
    HubPackageInstallRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new HubPackagesApi(configuration);

let packageName: string; // (default to undefined)
let hubPackageInstallRequest: HubPackageInstallRequest; // (optional)

const { status, data } = await apiInstance.installHubPackage(
    packageName,
    hubPackageInstallRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hubPackageInstallRequest** | **HubPackageInstallRequest**|  | |
| **packageName** | [**string**] |  | defaults to undefined|


### Return type

**HubPackageInstallResponse**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **listHubPackages**
> HubPackageListResponse listHubPackages()


### Example

```typescript
import {
    HubPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new HubPackagesApi(configuration);

let q: string; //Search query (optional) (default to undefined)
let tag: string; //Filter by tag (optional) (default to undefined)
let owner: string; //Filter by owner id (optional) (default to undefined)
let page: number; //1-based page index (optional) (default to 1)
let pageSize: number; //Page size (optional) (default to 20)

const { status, data } = await apiInstance.listHubPackages(
    q,
    tag,
    owner,
    page,
    pageSize
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **q** | [**string**] | Search query | (optional) defaults to undefined|
| **tag** | [**string**] | Filter by tag | (optional) defaults to undefined|
| **owner** | [**string**] | Filter by owner id | (optional) defaults to undefined|
| **page** | [**number**] | 1-based page index | (optional) defaults to 1|
| **pageSize** | [**number**] | Page size | (optional) defaults to 20|


### Return type

**HubPackageListResponse**

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

# **publishHubPackage**
> HubPackageVersionDetail publishHubPackage()


### Example

```typescript
import {
    HubPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new HubPackagesApi(configuration);

let file: File; // (default to undefined)
let visibility: HubVisibility; // (optional) (default to undefined)
let summary: string; // (optional) (default to undefined)
let readme: string; // (optional) (default to undefined)
let tags: Array<string>; // (optional) (default to undefined)

const { status, data } = await apiInstance.publishHubPackage(
    file,
    visibility,
    summary,
    readme,
    tags
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **file** | [**File**] |  | defaults to undefined|
| **visibility** | **HubVisibility** |  | (optional) defaults to undefined|
| **summary** | [**string**] |  | (optional) defaults to undefined|
| **readme** | [**string**] |  | (optional) defaults to undefined|
| **tags** | **Array&lt;string&gt;** |  | (optional) defaults to undefined|


### Return type

**HubPackageVersionDetail**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Created |  -  |
|**400** | Invalid input |  -  |
|**401** | Authentication required or credentials invalid |  -  |
|**403** | Authenticated but lacks required permissions |  -  |
|**409** | Conflict (e.g., idempotency-key reuse with different body) |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

