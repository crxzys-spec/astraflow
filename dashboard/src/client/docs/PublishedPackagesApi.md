# PublishedPackagesApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**deletePublishedPackageTag**](#deletepublishedpackagetag) | **DELETE** /api/v1/published-packages/{packageName}/tags/{tag} | Delete published package dist-tag|
|[**downloadPublishedPackage**](#downloadpublishedpackage) | **GET** /api/v1/published-packages/{packageName}/archive | Download published package archive|
|[**gcPublishedPackages**](#gcpublishedpackages) | **POST** /api/v1/published-packages/gc | Garbage collect published package versions|
|[**getPublishedPackage**](#getpublishedpackage) | **GET** /api/v1/published-packages/{packageName} | Get published package detail|
|[**getPublishedPackageRegistry**](#getpublishedpackageregistry) | **GET** /api/v1/published-packages/{packageName}/registry | Get published package registry metadata|
|[**listPublishedPackages**](#listpublishedpackages) | **GET** /api/v1/published-packages | List published packages|
|[**reservePublishedPackage**](#reservepublishedpackage) | **POST** /api/v1/published-packages/{packageName}/reserve | Reserve a published package name|
|[**setPublishedPackageTag**](#setpublishedpackagetag) | **PUT** /api/v1/published-packages/{packageName}/tags/{tag} | Set published package dist-tag|
|[**setPublishedPackageVersionStatus**](#setpublishedpackageversionstatus) | **PATCH** /api/v1/published-packages/{packageName}/versions/{version} | Set published package version status|
|[**transferPublishedPackage**](#transferpublishedpackage) | **POST** /api/v1/published-packages/{packageName}/transfer | Transfer published package ownership|
|[**updatePublishedPackageVisibility**](#updatepublishedpackagevisibility) | **PATCH** /api/v1/published-packages/{packageName}/visibility | Update published package visibility|
|[**uploadPublishedPackage**](#uploadpublishedpackage) | **POST** /api/v1/published-packages | Upload a published package archive|

# **deletePublishedPackageTag**
> deletePublishedPackageTag()


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

let packageName: string; // (default to undefined)
let tag: string; // (default to undefined)

const { status, data } = await apiInstance.deletePublishedPackageTag(
    packageName,
    tag
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageName** | [**string**] |  | defaults to undefined|
| **tag** | [**string**] |  | defaults to undefined|


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
|**403** | Authenticated but lacks required permissions |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **downloadPublishedPackage**
> File downloadPublishedPackage()


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

let packageName: string; // (default to undefined)
let version: string; //Specific package version to retrieve. Defaults to the latest available version. (optional) (default to undefined)

const { status, data } = await apiInstance.downloadPublishedPackage(
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

**File**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/zip, application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  * X-Package-Archive-Sha256 - SHA256 of the stored package archive <br>  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **gcPublishedPackages**
> PublishedPackageGcResult gcPublishedPackages(publishedPackageGcRequest)


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration,
    PublishedPackageGcRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

let publishedPackageGcRequest: PublishedPackageGcRequest; //

const { status, data } = await apiInstance.gcPublishedPackages(
    publishedPackageGcRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **publishedPackageGcRequest** | **PublishedPackageGcRequest**|  | |


### Return type

**PublishedPackageGcResult**

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
|**403** | Authenticated but lacks required permissions |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getPublishedPackage**
> PackageDetail getPublishedPackage()


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

let packageName: string; // (default to undefined)
let version: string; //Specific package version to retrieve. Defaults to the latest available version. (optional) (default to undefined)

const { status, data } = await apiInstance.getPublishedPackage(
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
|**200** | OK |  * X-Package-Archive-Sha256 - SHA256 of the stored package archive <br>  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getPublishedPackageRegistry**
> PublishedPackageRegistry getPublishedPackageRegistry()


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

let packageName: string; // (default to undefined)

const { status, data } = await apiInstance.getPublishedPackageRegistry(
    packageName
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageName** | [**string**] |  | defaults to undefined|


### Return type

**PublishedPackageRegistry**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |
|**403** | Authenticated but lacks required permissions |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **listPublishedPackages**
> PackageList listPublishedPackages()


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

const { status, data } = await apiInstance.listPublishedPackages();
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

# **reservePublishedPackage**
> PublishedPackageRegistry reservePublishedPackage()


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration,
    PublishedPackageReserveRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

let packageName: string; // (default to undefined)
let publishedPackageReserveRequest: PublishedPackageReserveRequest; // (optional)

const { status, data } = await apiInstance.reservePublishedPackage(
    packageName,
    publishedPackageReserveRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **publishedPackageReserveRequest** | **PublishedPackageReserveRequest**|  | |
| **packageName** | [**string**] |  | defaults to undefined|


### Return type

**PublishedPackageRegistry**

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
|**403** | Authenticated but lacks required permissions |  -  |
|**409** | Conflict (e.g., idempotency-key reuse with different body) |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **setPublishedPackageTag**
> setPublishedPackageTag(publishedPackageTagRequest)


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration,
    PublishedPackageTagRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

let packageName: string; // (default to undefined)
let tag: string; // (default to undefined)
let publishedPackageTagRequest: PublishedPackageTagRequest; //

const { status, data } = await apiInstance.setPublishedPackageTag(
    packageName,
    tag,
    publishedPackageTagRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **publishedPackageTagRequest** | **PublishedPackageTagRequest**|  | |
| **packageName** | [**string**] |  | defaults to undefined|
| **tag** | [**string**] |  | defaults to undefined|


### Return type

void (empty response body)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**204** | Updated |  -  |
|**400** | Invalid input |  -  |
|**403** | Authenticated but lacks required permissions |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **setPublishedPackageVersionStatus**
> PackageDetail setPublishedPackageVersionStatus(publishedPackageStatusRequest)


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration,
    PublishedPackageStatusRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

let packageName: string; // (default to undefined)
let version: string; // (default to undefined)
let publishedPackageStatusRequest: PublishedPackageStatusRequest; //

const { status, data } = await apiInstance.setPublishedPackageVersionStatus(
    packageName,
    version,
    publishedPackageStatusRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **publishedPackageStatusRequest** | **PublishedPackageStatusRequest**|  | |
| **packageName** | [**string**] |  | defaults to undefined|
| **version** | [**string**] |  | defaults to undefined|


### Return type

**PackageDetail**

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
|**403** | Authenticated but lacks required permissions |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **transferPublishedPackage**
> PublishedPackageRegistry transferPublishedPackage(publishedPackageTransferRequest)


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration,
    PublishedPackageTransferRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

let packageName: string; // (default to undefined)
let publishedPackageTransferRequest: PublishedPackageTransferRequest; //

const { status, data } = await apiInstance.transferPublishedPackage(
    packageName,
    publishedPackageTransferRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **publishedPackageTransferRequest** | **PublishedPackageTransferRequest**|  | |
| **packageName** | [**string**] |  | defaults to undefined|


### Return type

**PublishedPackageRegistry**

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
|**403** | Authenticated but lacks required permissions |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **updatePublishedPackageVisibility**
> PublishedPackageRegistry updatePublishedPackageVisibility(publishedPackageVisibilityRequest)


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration,
    PublishedPackageVisibilityRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

let packageName: string; // (default to undefined)
let publishedPackageVisibilityRequest: PublishedPackageVisibilityRequest; //

const { status, data } = await apiInstance.updatePublishedPackageVisibility(
    packageName,
    publishedPackageVisibilityRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **publishedPackageVisibilityRequest** | **PublishedPackageVisibilityRequest**|  | |
| **packageName** | [**string**] |  | defaults to undefined|


### Return type

**PublishedPackageRegistry**

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
|**403** | Authenticated but lacks required permissions |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **uploadPublishedPackage**
> PackageDetail uploadPublishedPackage()


### Example

```typescript
import {
    PublishedPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PublishedPackagesApi(configuration);

let file: File; // (default to undefined)

const { status, data } = await apiInstance.uploadPublishedPackage(
    file
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **file** | [**File**] |  | defaults to undefined|


### Return type

**PackageDetail**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  * X-Package-Archive-Sha256 - SHA256 of the stored package archive <br>  |
|**400** | Invalid input |  -  |
|**409** | Conflict (e.g., idempotency-key reuse with different body) |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

