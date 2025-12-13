# WorkflowsApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**deleteWorkflow**](#deleteworkflow) | **DELETE** /api/v1/workflows/{workflowId} | Soft delete workflow|
|[**getWorkflow**](#getworkflow) | **GET** /api/v1/workflows/{workflowId} | Read stored workflow (latest)|
|[**getWorkflowPreview**](#getworkflowpreview) | **GET** /api/v1/workflows/{workflowId}/preview | Get workflow canvas preview|
|[**listWorkflows**](#listworkflows) | **GET** /api/v1/workflows | List stored workflows (paginated)|
|[**persistWorkflow**](#persistworkflow) | **POST** /api/v1/workflows | Persist a workflow for editor storage (no versioning)|
|[**setWorkflowPreview**](#setworkflowpreview) | **PUT** /api/v1/workflows/{workflowId}/preview | Set or clear workflow canvas preview|

# **deleteWorkflow**
> deleteWorkflow()

Marks the workflow record as deleted so it is hidden from listings and future reads.

### Example

```typescript
import {
    WorkflowsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowsApi(configuration);

let workflowId: string; // (default to undefined)

const { status, data } = await apiInstance.deleteWorkflow(
    workflowId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflowId** | [**string**] |  | defaults to undefined|


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
|**204** | Workflow deleted |  -  |
|**403** | Authenticated but lacks required permissions |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getWorkflow**
> Workflow getWorkflow()


### Example

```typescript
import {
    WorkflowsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowsApi(configuration);

let workflowId: string; // (default to undefined)

const { status, data } = await apiInstance.getWorkflow(
    workflowId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflowId** | [**string**] |  | defaults to undefined|


### Return type

**Workflow**

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

# **getWorkflowPreview**
> WorkflowPreview getWorkflowPreview()


### Example

```typescript
import {
    WorkflowsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowsApi(configuration);

let workflowId: string; // (default to undefined)

const { status, data } = await apiInstance.getWorkflowPreview(
    workflowId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflowId** | [**string**] |  | defaults to undefined|


### Return type

**WorkflowPreview**

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

# **listWorkflows**
> WorkflowList listWorkflows()


### Example

```typescript
import {
    WorkflowsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowsApi(configuration);

let limit: number; // (optional) (default to 50)
let cursor: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.listWorkflows(
    limit,
    cursor
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **limit** | [**number**] |  | (optional) defaults to 50|
| **cursor** | [**string**] |  | (optional) defaults to undefined|


### Return type

**WorkflowList**

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

# **persistWorkflow**
> WorkflowRef persistWorkflow(workflow)


### Example

```typescript
import {
    WorkflowsApi,
    Configuration,
    Workflow
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowsApi(configuration);

let workflow: Workflow; //
let idempotencyKey: string; //Optional idempotency key for safe retries; if reused with a different body, return 409 (optional) (default to undefined)

const { status, data } = await apiInstance.persistWorkflow(
    workflow,
    idempotencyKey
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflow** | **Workflow**|  | |
| **idempotencyKey** | [**string**] | Optional idempotency key for safe retries; if reused with a different body, return 409 | (optional) defaults to undefined|


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
|**400** | Invalid input |  -  |
|**409** | Conflict (e.g., idempotency-key reuse with different body) |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **setWorkflowPreview**
> WorkflowPreview setWorkflowPreview(workflowPreview)


### Example

```typescript
import {
    WorkflowsApi,
    Configuration,
    WorkflowPreview
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowsApi(configuration);

let workflowId: string; // (default to undefined)
let workflowPreview: WorkflowPreview; //

const { status, data } = await apiInstance.setWorkflowPreview(
    workflowId,
    workflowPreview
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workflowPreview** | **WorkflowPreview**|  | |
| **workflowId** | [**string**] |  | defaults to undefined|


### Return type

**WorkflowPreview**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Updated |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

