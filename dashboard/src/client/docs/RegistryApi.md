# RegistryApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**getRegistryAccount**](#getregistryaccount) | **GET** /api/v1/registry/account | Get linked registry account|
|[**importRegistryWorkflow**](#importregistryworkflow) | **POST** /api/v1/registry/workflows/import | Import a registry workflow into the platform|
|[**linkRegistryAccount**](#linkregistryaccount) | **POST** /api/v1/registry/account | Link registry account|
|[**unlinkRegistryAccount**](#unlinkregistryaccount) | **DELETE** /api/v1/registry/account | Unlink registry account|

# **getRegistryAccount**
> RegistryAccountLink getRegistryAccount()


### Example

```typescript
import {
    RegistryApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new RegistryApi(configuration);

const { status, data } = await apiInstance.getRegistryAccount();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**RegistryAccountLink**

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

# **importRegistryWorkflow**
> RegistryWorkflowImportResponse importRegistryWorkflow(registryWorkflowImportRequest)


### Example

```typescript
import {
    RegistryApi,
    Configuration,
    RegistryWorkflowImportRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new RegistryApi(configuration);

let registryWorkflowImportRequest: RegistryWorkflowImportRequest; //

const { status, data } = await apiInstance.importRegistryWorkflow(
    registryWorkflowImportRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **registryWorkflowImportRequest** | **RegistryWorkflowImportRequest**|  | |


### Return type

**RegistryWorkflowImportResponse**

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
|**404** | Resource not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **linkRegistryAccount**
> RegistryAccountLink linkRegistryAccount(registryAccountLinkRequest)


### Example

```typescript
import {
    RegistryApi,
    Configuration,
    RegistryAccountLinkRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new RegistryApi(configuration);

let registryAccountLinkRequest: RegistryAccountLinkRequest; //

const { status, data } = await apiInstance.linkRegistryAccount(
    registryAccountLinkRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **registryAccountLinkRequest** | **RegistryAccountLinkRequest**|  | |


### Return type

**RegistryAccountLink**

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

# **unlinkRegistryAccount**
> unlinkRegistryAccount()


### Example

```typescript
import {
    RegistryApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new RegistryApi(configuration);

const { status, data } = await apiInstance.unlinkRegistryAccount();
```

### Parameters
This endpoint does not have any parameters.


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

