# WorkersApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**getWorker**](#getworker) | **GET** /api/v1/workers/{workerName} | Get worker snapshot|
|[**listWorkers**](#listworkers) | **GET** /api/v1/workers | List workers (scheduler view)|
|[**sendWorkerCommand**](#sendworkercommand) | **POST** /api/v1/workers/{workerName}/commands | Enqueue admin command (drain/rebind/pkg.install/pkg.uninstall)|

# **getWorker**
> Worker getWorker()


### Example

```typescript
import {
    WorkersApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkersApi(configuration);

let workerName: string; // (default to undefined)

const { status, data } = await apiInstance.getWorker(
    workerName
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workerName** | [**string**] |  | defaults to undefined|


### Return type

**Worker**

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

# **listWorkers**
> ListWorkers200Response listWorkers()


### Example

```typescript
import {
    WorkersApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkersApi(configuration);

let queue: string; // (optional) (default to undefined)
let connected: boolean; // (optional) (default to undefined)
let registered: boolean; // (optional) (default to undefined)
let healthy: boolean; // (optional) (default to undefined)
let packageName: string; // (optional) (default to undefined)
let packageVersion: string; // (optional) (default to undefined)
let packageStatus: WorkerPackageStatus; // (optional) (default to undefined)
let maxHeartbeatAgeSeconds: number; // (optional) (default to undefined)
let maxInflight: number; // (optional) (default to undefined)
let maxLatencyMs: number; // (optional) (default to undefined)
let limit: number; // (optional) (default to 50)
let cursor: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.listWorkers(
    queue,
    connected,
    registered,
    healthy,
    packageName,
    packageVersion,
    packageStatus,
    maxHeartbeatAgeSeconds,
    maxInflight,
    maxLatencyMs,
    limit,
    cursor
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **queue** | [**string**] |  | (optional) defaults to undefined|
| **connected** | [**boolean**] |  | (optional) defaults to undefined|
| **registered** | [**boolean**] |  | (optional) defaults to undefined|
| **healthy** | [**boolean**] |  | (optional) defaults to undefined|
| **packageName** | [**string**] |  | (optional) defaults to undefined|
| **packageVersion** | [**string**] |  | (optional) defaults to undefined|
| **packageStatus** | **WorkerPackageStatus** |  | (optional) defaults to undefined|
| **maxHeartbeatAgeSeconds** | [**number**] |  | (optional) defaults to undefined|
| **maxInflight** | [**number**] |  | (optional) defaults to undefined|
| **maxLatencyMs** | [**number**] |  | (optional) defaults to undefined|
| **limit** | [**number**] |  | (optional) defaults to 50|
| **cursor** | [**string**] |  | (optional) defaults to undefined|


### Return type

**ListWorkers200Response**

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

# **sendWorkerCommand**
> CommandRef sendWorkerCommand(workerCommand)


### Example

```typescript
import {
    WorkersApi,
    Configuration,
    WorkerCommand
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkersApi(configuration);

let workerName: string; // (default to undefined)
let workerCommand: WorkerCommand; //
let idempotencyKey: string; //Optional idempotency key for safe retries; if reused with a different body, return 409 (optional) (default to undefined)

const { status, data } = await apiInstance.sendWorkerCommand(
    workerName,
    workerCommand,
    idempotencyKey
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **workerCommand** | **WorkerCommand**|  | |
| **workerName** | [**string**] |  | defaults to undefined|
| **idempotencyKey** | [**string**] | Optional idempotency key for safe retries; if reused with a different body, return 409 | (optional) defaults to undefined|


### Return type

**CommandRef**

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
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

