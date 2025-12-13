# RunsApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**cancelRun**](#cancelrun) | **POST** /api/v1/runs/{runId}/cancel | Cancel a run|
|[**getRun**](#getrun) | **GET** /api/v1/runs/{runId} | Get run summary|
|[**getRunDefinition**](#getrundefinition) | **GET** /api/v1/runs/{runId}/definition | Get the immutable workflow snapshot used by this run|
|[**listRuns**](#listruns) | **GET** /api/v1/runs | List runs (paginated)|
|[**startRun**](#startrun) | **POST** /api/v1/runs | Start a run using the in-memory workflow snapshot|

# **cancelRun**
> RunRef cancelRun()


### Example

```typescript
import {
    RunsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new RunsApi(configuration);

let runId: string; // (default to undefined)

const { status, data } = await apiInstance.cancelRun(
    runId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **runId** | [**string**] |  | defaults to undefined|


### Return type

**RunRef**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | Accepted |  -  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getRun**
> Run getRun()


### Example

```typescript
import {
    RunsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new RunsApi(configuration);

let runId: string; // (default to undefined)

const { status, data } = await apiInstance.getRun(
    runId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **runId** | [**string**] |  | defaults to undefined|


### Return type

**Run**

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

# **getRunDefinition**
> Workflow getRunDefinition()


### Example

```typescript
import {
    RunsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new RunsApi(configuration);

let runId: string; // (default to undefined)

const { status, data } = await apiInstance.getRunDefinition(
    runId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **runId** | [**string**] |  | defaults to undefined|


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
|**200** | OK |  * ETag - Weak ETag based on definitionHash <br>  |
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **listRuns**
> RunList listRuns()


### Example

```typescript
import {
    RunsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new RunsApi(configuration);

let limit: number; // (optional) (default to 50)
let cursor: string; // (optional) (default to undefined)
let status: RunStatus; // (optional) (default to undefined)
let clientId: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.listRuns(
    limit,
    cursor,
    status,
    clientId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **limit** | [**number**] |  | (optional) defaults to 50|
| **cursor** | [**string**] |  | (optional) defaults to undefined|
| **status** | **RunStatus** |  | (optional) defaults to undefined|
| **clientId** | [**string**] |  | (optional) defaults to undefined|


### Return type

**RunList**

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

# **startRun**
> RunRef startRun(runStartRequest)


### Example

```typescript
import {
    RunsApi,
    Configuration,
    RunStartRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new RunsApi(configuration);

let runStartRequest: RunStartRequest; //
let idempotencyKey: string; //Optional idempotency key for safe retries; if reused with a different body, return 409 (optional) (default to undefined)

const { status, data } = await apiInstance.startRun(
    runStartRequest,
    idempotencyKey
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **runStartRequest** | **RunStartRequest**|  | |
| **idempotencyKey** | [**string**] | Optional idempotency key for safe retries; if reused with a different body, return 409 | (optional) defaults to undefined|


### Return type

**RunRef**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | Accepted |  -  |
|**400** | Invalid input |  -  |
|**409** | Conflict (e.g., idempotency-key reuse with different body) |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

