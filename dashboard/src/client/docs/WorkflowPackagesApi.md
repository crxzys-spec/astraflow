# WorkflowPackagesApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**cloneWorkflowPackage**](#cloneworkflowpackage) | **POST** /api/v1/workflow-packages/{packageId}/clone | Clone a workflow package version into the caller\&#39;s workspace|
|[**deleteWorkflowPackage**](#deleteworkflowpackage) | **DELETE** /api/v1/workflow-packages/{packageId} | Delete a workflow package|
|[**getWorkflowPackage**](#getworkflowpackage) | **GET** /api/v1/workflow-packages/{packageId} | Get a workflow package detail|
|[**listWorkflowPackageVersions**](#listworkflowpackageversions) | **GET** /api/v1/workflow-packages/{packageId}/versions | List versions for a workflow package|
|[**listWorkflowPackages**](#listworkflowpackages) | **GET** /api/v1/workflow-packages | List published workflow packages|
|[**publishWorkflow**](#publishworkflow) | **POST** /api/v1/workflows/{workflowId}/publish | Publish a workflow draft to the Store|

# **cloneWorkflowPackage**
> WorkflowRef cloneWorkflowPackage()


### Example

```typescript
import {
    WorkflowPackagesApi,
    Configuration,
    WorkflowPackageCloneRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowPackagesApi(configuration);

let packageId: string; // (default to undefined)
let workflowPackageCloneRequest: WorkflowPackageCloneRequest; // (optional)

const { status, data } = await apiInstance.cloneWorkflowPackage(
    packageId,
    workflowPackageCloneRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflowPackageCloneRequest** | **WorkflowPackageCloneRequest**|  | |
| **packageId** | [**string**] |  | defaults to undefined|


### Return type

**WorkflowRef**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Created |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **deleteWorkflowPackage**
> deleteWorkflowPackage()


### Example

```typescript
import {
    WorkflowPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowPackagesApi(configuration);

let packageId: string; // (default to undefined)

const { status, data } = await apiInstance.deleteWorkflowPackage(
    packageId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageId** | [**string**] |  | defaults to undefined|


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

# **getWorkflowPackage**
> WorkflowPackageDetail getWorkflowPackage()


### Example

```typescript
import {
    WorkflowPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowPackagesApi(configuration);

let packageId: string; // (default to undefined)

const { status, data } = await apiInstance.getWorkflowPackage(
    packageId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageId** | [**string**] |  | defaults to undefined|


### Return type

**WorkflowPackageDetail**

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

# **listWorkflowPackageVersions**
> WorkflowPackageVersionList listWorkflowPackageVersions()


### Example

```typescript
import {
    WorkflowPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowPackagesApi(configuration);

let packageId: string; // (default to undefined)

const { status, data } = await apiInstance.listWorkflowPackageVersions(
    packageId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **packageId** | [**string**] |  | defaults to undefined|


### Return type

**WorkflowPackageVersionList**

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

# **listWorkflowPackages**
> WorkflowPackageList listWorkflowPackages()


### Example

```typescript
import {
    WorkflowPackagesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowPackagesApi(configuration);

let limit: number; // (optional) (default to 50)
let cursor: string; // (optional) (default to undefined)
let owner: string; //Filter by owner id; use `me` for the caller\'s id. (optional) (default to undefined)
let visibility: string; //Filter by visibility (private, internal, public). (optional) (default to undefined)
let search: string; //Full-text search across slug, display name, and summary. (optional) (default to undefined)

const { status, data } = await apiInstance.listWorkflowPackages(
    limit,
    cursor,
    owner,
    visibility,
    search
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **limit** | [**number**] |  | (optional) defaults to 50|
| **cursor** | [**string**] |  | (optional) defaults to undefined|
| **owner** | [**string**] | Filter by owner id; use &#x60;me&#x60; for the caller\&#39;s id. | (optional) defaults to undefined|
| **visibility** | [**string**] | Filter by visibility (private, internal, public). | (optional) defaults to undefined|
| **search** | [**string**] | Full-text search across slug, display name, and summary. | (optional) defaults to undefined|


### Return type

**WorkflowPackageList**

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

# **publishWorkflow**
> WorkflowPublishResponse publishWorkflow(workflowPublishRequest)


### Example

```typescript
import {
    WorkflowPackagesApi,
    Configuration,
    WorkflowPublishRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowPackagesApi(configuration);

let workflowId: string; // (default to undefined)
let workflowPublishRequest: WorkflowPublishRequest; //

const { status, data } = await apiInstance.publishWorkflow(
    workflowId,
    workflowPublishRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflowPublishRequest** | **WorkflowPublishRequest**|  | |
| **workflowId** | [**string**] |  | defaults to undefined|


### Return type

**WorkflowPublishResponse**

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
|**409** | Conflict (e.g., idempotency-key reuse with different body) |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

