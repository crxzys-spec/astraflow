# AuditApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**listAuditEvents**](#listauditevents) | **GET** /api/v1/audit-events | List audit events|

# **listAuditEvents**
> AuditEventList listAuditEvents()


### Example

```typescript
import {
    AuditApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AuditApi(configuration);

let limit: number; // (optional) (default to 50)
let cursor: string; //Reserved for future pagination (optional) (default to undefined)
let action: string; //Filter by action name (optional) (default to undefined)
let actorId: string; //Filter by actor id (optional) (default to undefined)
let targetType: string; //Filter by target type (optional) (default to undefined)

const { status, data } = await apiInstance.listAuditEvents(
    limit,
    cursor,
    action,
    actorId,
    targetType
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **limit** | [**number**] |  | (optional) defaults to 50|
| **cursor** | [**string**] | Reserved for future pagination | (optional) defaults to undefined|
| **action** | [**string**] | Filter by action name | (optional) defaults to undefined|
| **actorId** | [**string**] | Filter by actor id | (optional) defaults to undefined|
| **targetType** | [**string**] | Filter by target type | (optional) defaults to undefined|


### Return type

**AuditEventList**

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

