# ResourcesApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**completeResourceUpload**](#completeresourceupload) | **POST** /api/v1/resources/uploads/{uploadId}/complete | Complete resource upload|
|[**createResourceGrant**](#createresourcegrant) | **POST** /api/v1/resource-grants | Create resource grant|
|[**createResourceUpload**](#createresourceupload) | **POST** /api/v1/resources/uploads | Create resource upload session|
|[**deleteResource**](#deleteresource) | **DELETE** /api/v1/resources/{resourceId} | Delete resource|
|[**deleteResourceGrant**](#deleteresourcegrant) | **DELETE** /api/v1/resource-grants/{grantId} | Delete resource grant|
|[**deleteResourceUpload**](#deleteresourceupload) | **DELETE** /api/v1/resources/uploads/{uploadId} | Abort resource upload session|
|[**downloadResource**](#downloadresource) | **GET** /api/v1/resources/{resourceId}/download | Download resource|
|[**getResource**](#getresource) | **GET** /api/v1/resources/{resourceId} | Get resource metadata|
|[**getResourceGrant**](#getresourcegrant) | **GET** /api/v1/resource-grants/{grantId} | Get resource grant|
|[**getResourceUpload**](#getresourceupload) | **GET** /api/v1/resources/uploads/{uploadId} | Get resource upload session|
|[**listResourceGrants**](#listresourcegrants) | **GET** /api/v1/resource-grants | List resource grants|
|[**listResources**](#listresources) | **GET** /api/v1/resources | List resources|
|[**uploadResource**](#uploadresource) | **POST** /api/v1/resources | Upload resource|
|[**uploadResourcePart**](#uploadresourcepart) | **PUT** /api/v1/resources/uploads/{uploadId}/parts/{partNumber} | Upload resource part|

# **completeResourceUpload**
> Resource completeResourceUpload()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let uploadId: string; // (default to undefined)

const { status, data } = await apiInstance.completeResourceUpload(
    uploadId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **uploadId** | [**string**] |  | defaults to undefined|


### Return type

**Resource**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Created |  -  |
|**400** | Invalid input |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **createResourceGrant**
> ResourceGrant createResourceGrant(resourceGrantCreateRequest)


### Example

```typescript
import {
    ResourcesApi,
    Configuration,
    ResourceGrantCreateRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let resourceGrantCreateRequest: ResourceGrantCreateRequest; //

const { status, data } = await apiInstance.createResourceGrant(
    resourceGrantCreateRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **resourceGrantCreateRequest** | **ResourceGrantCreateRequest**|  | |


### Return type

**ResourceGrant**

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

# **createResourceUpload**
> ResourceUploadSession createResourceUpload(resourceUploadInitRequest)


### Example

```typescript
import {
    ResourcesApi,
    Configuration,
    ResourceUploadInitRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let resourceUploadInitRequest: ResourceUploadInitRequest; //

const { status, data } = await apiInstance.createResourceUpload(
    resourceUploadInitRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **resourceUploadInitRequest** | **ResourceUploadInitRequest**|  | |


### Return type

**ResourceUploadSession**

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

# **deleteResource**
> deleteResource()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let resourceId: string; // (default to undefined)

const { status, data } = await apiInstance.deleteResource(
    resourceId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **resourceId** | [**string**] |  | defaults to undefined|


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

# **deleteResourceGrant**
> deleteResourceGrant()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let grantId: string; // (default to undefined)

const { status, data } = await apiInstance.deleteResourceGrant(
    grantId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **grantId** | [**string**] |  | defaults to undefined|


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

# **deleteResourceUpload**
> deleteResourceUpload()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let uploadId: string; // (default to undefined)

const { status, data } = await apiInstance.deleteResourceUpload(
    uploadId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **uploadId** | [**string**] |  | defaults to undefined|


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

# **downloadResource**
> File downloadResource()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let resourceId: string; // (default to undefined)

const { status, data } = await apiInstance.downloadResource(
    resourceId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **resourceId** | [**string**] |  | defaults to undefined|


### Return type

**File**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/octet-stream, application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getResource**
> Resource getResource()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let resourceId: string; // (default to undefined)

const { status, data } = await apiInstance.getResource(
    resourceId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **resourceId** | [**string**] |  | defaults to undefined|


### Return type

**Resource**

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

# **getResourceGrant**
> ResourceGrant getResourceGrant()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let grantId: string; // (default to undefined)

const { status, data } = await apiInstance.getResourceGrant(
    grantId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **grantId** | [**string**] |  | defaults to undefined|


### Return type

**ResourceGrant**

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

# **getResourceUpload**
> ResourceUploadSession getResourceUpload()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let uploadId: string; // (default to undefined)

const { status, data } = await apiInstance.getResourceUpload(
    uploadId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **uploadId** | [**string**] |  | defaults to undefined|


### Return type

**ResourceUploadSession**

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

# **listResourceGrants**
> ResourceGrantList listResourceGrants()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let workflowId: string; // (optional) (default to undefined)
let packageName: string; // (optional) (default to undefined)
let packageVersion: string; // (optional) (default to undefined)
let resourceKey: string; // (optional) (default to undefined)
let scope: ResourceGrantScope; // (optional) (default to undefined)
let resourceId: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.listResourceGrants(
    workflowId,
    packageName,
    packageVersion,
    resourceKey,
    scope,
    resourceId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflowId** | [**string**] |  | (optional) defaults to undefined|
| **packageName** | [**string**] |  | (optional) defaults to undefined|
| **packageVersion** | [**string**] |  | (optional) defaults to undefined|
| **resourceKey** | [**string**] |  | (optional) defaults to undefined|
| **scope** | **ResourceGrantScope** |  | (optional) defaults to undefined|
| **resourceId** | [**string**] |  | (optional) defaults to undefined|


### Return type

**ResourceGrantList**

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

# **listResources**
> ResourceList listResources()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let limit: number; // (optional) (default to 50)
let cursor: string; // (optional) (default to undefined)
let search: string; // (optional) (default to undefined)
let ownerId: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.listResources(
    limit,
    cursor,
    search,
    ownerId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **limit** | [**number**] |  | (optional) defaults to 50|
| **cursor** | [**string**] |  | (optional) defaults to undefined|
| **search** | [**string**] |  | (optional) defaults to undefined|
| **ownerId** | [**string**] |  | (optional) defaults to undefined|


### Return type

**ResourceList**

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

# **uploadResource**
> Resource uploadResource()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let file: File; // (default to undefined)
let provider: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.uploadResource(
    file,
    provider
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **file** | [**File**] |  | defaults to undefined|
| **provider** | [**string**] |  | (optional) defaults to undefined|


### Return type

**Resource**

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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **uploadResourcePart**
> ResourceUploadPart uploadResourcePart()


### Example

```typescript
import {
    ResourcesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ResourcesApi(configuration);

let uploadId: string; // (default to undefined)
let partNumber: number; // (default to undefined)
let file: File; // (default to undefined)

const { status, data } = await apiInstance.uploadResourcePart(
    uploadId,
    partNumber,
    file
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **uploadId** | [**string**] |  | defaults to undefined|
| **partNumber** | [**number**] |  | defaults to undefined|
| **file** | [**File**] |  | defaults to undefined|


### Return type

**ResourceUploadPart**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |
|**400** | Invalid input |  -  |
|**404** | Resource not found |  -  |
|**409** | Conflict (e.g., idempotency-key reuse with different body) |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

