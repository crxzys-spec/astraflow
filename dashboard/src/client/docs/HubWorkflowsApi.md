# HubWorkflowsApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**getHubWorkflow**](#gethubworkflow) | **GET** /api/v1/hub/workflows/{workflowId} | Get hub workflow detail|
|[**getHubWorkflowDefinition**](#gethubworkflowdefinition) | **GET** /api/v1/hub/workflows/{workflowId}/versions/{versionId}/definition | Get hub workflow definition|
|[**getHubWorkflowVersion**](#gethubworkflowversion) | **GET** /api/v1/hub/workflows/{workflowId}/versions/{versionId} | Get hub workflow version detail|
|[**importHubWorkflow**](#importhubworkflow) | **POST** /api/v1/hub/workflows/{workflowId}/import | Import a hub workflow into the local workspace|
|[**listHubWorkflowVersions**](#listhubworkflowversions) | **GET** /api/v1/hub/workflows/{workflowId}/versions | List hub workflow versions|
|[**listHubWorkflows**](#listhubworkflows) | **GET** /api/v1/hub/workflows | List hub workflows|
|[**publishHubWorkflow**](#publishhubworkflow) | **POST** /api/v1/hub/workflows | Publish a workflow to Hub|

# **getHubWorkflow**
> HubWorkflowDetail getHubWorkflow()


### Example

```typescript
import {
    HubWorkflowsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new HubWorkflowsApi(configuration);

let workflowId: string; // (default to undefined)

const { status, data } = await apiInstance.getHubWorkflow(
    workflowId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflowId** | [**string**] |  | defaults to undefined|


### Return type

**HubWorkflowDetail**

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

# **getHubWorkflowDefinition**
> { [key: string]: any; } getHubWorkflowDefinition()


### Example

```typescript
import {
    HubWorkflowsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new HubWorkflowsApi(configuration);

let workflowId: string; // (default to undefined)
let versionId: string; // (default to undefined)

const { status, data } = await apiInstance.getHubWorkflowDefinition(
    workflowId,
    versionId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflowId** | [**string**] |  | defaults to undefined|
| **versionId** | [**string**] |  | defaults to undefined|


### Return type

**{ [key: string]: any; }**

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

# **getHubWorkflowVersion**
> HubWorkflowVersionDetail getHubWorkflowVersion()


### Example

```typescript
import {
    HubWorkflowsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new HubWorkflowsApi(configuration);

let workflowId: string; // (default to undefined)
let versionId: string; // (default to undefined)

const { status, data } = await apiInstance.getHubWorkflowVersion(
    workflowId,
    versionId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflowId** | [**string**] |  | defaults to undefined|
| **versionId** | [**string**] |  | defaults to undefined|


### Return type

**HubWorkflowVersionDetail**

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

# **importHubWorkflow**
> HubWorkflowImportResponse importHubWorkflow()


### Example

```typescript
import {
    HubWorkflowsApi,
    Configuration,
    HubWorkflowImportRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new HubWorkflowsApi(configuration);

let workflowId: string; // (default to undefined)
let hubWorkflowImportRequest: HubWorkflowImportRequest; // (optional)

const { status, data } = await apiInstance.importHubWorkflow(
    workflowId,
    hubWorkflowImportRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hubWorkflowImportRequest** | **HubWorkflowImportRequest**|  | |
| **workflowId** | [**string**] |  | defaults to undefined|


### Return type

**HubWorkflowImportResponse**

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

# **listHubWorkflowVersions**
> HubWorkflowVersionList listHubWorkflowVersions()


### Example

```typescript
import {
    HubWorkflowsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new HubWorkflowsApi(configuration);

let workflowId: string; // (default to undefined)

const { status, data } = await apiInstance.listHubWorkflowVersions(
    workflowId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflowId** | [**string**] |  | defaults to undefined|


### Return type

**HubWorkflowVersionList**

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

# **listHubWorkflows**
> HubWorkflowListResponse listHubWorkflows()


### Example

```typescript
import {
    HubWorkflowsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new HubWorkflowsApi(configuration);

let q: string; //Search query (optional) (default to undefined)
let tag: string; //Filter by tag (optional) (default to undefined)
let owner: string; //Filter by owner id (optional) (default to undefined)
let page: number; //1-based page index (optional) (default to 1)
let pageSize: number; //Page size (optional) (default to 20)

const { status, data } = await apiInstance.listHubWorkflows(
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

**HubWorkflowListResponse**

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

# **publishHubWorkflow**
> HubWorkflowPublishResponse publishHubWorkflow(hubWorkflowPublishRequest)


### Example

```typescript
import {
    HubWorkflowsApi,
    Configuration,
    HubWorkflowPublishRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new HubWorkflowsApi(configuration);

let hubWorkflowPublishRequest: HubWorkflowPublishRequest; //

const { status, data } = await apiInstance.publishHubWorkflow(
    hubWorkflowPublishRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hubWorkflowPublishRequest** | **HubWorkflowPublishRequest**|  | |


### Return type

**HubWorkflowPublishResponse**

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
|**401** | Authentication required or credentials invalid |  -  |
|**403** | Authenticated but lacks required permissions |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

