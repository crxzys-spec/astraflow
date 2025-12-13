# EventsApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**sseGlobalEvents**](#sseglobalevents) | **GET** /api/v1/events | Global Server-Sent Events stream (firehose; no query parameters)|

# **sseGlobalEvents**
> string sseGlobalEvents()


### Example

```typescript
import {
    EventsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new EventsApi(configuration);

let clientSessionId: string; //Frontend-generated session identifier (UUID) used to route SSE events. (default to undefined)
let lastEventID: string; //Resume SSE from a specific monotonic event id (optional) (default to undefined)

const { status, data } = await apiInstance.sseGlobalEvents(
    clientSessionId,
    lastEventID
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **clientSessionId** | [**string**] | Frontend-generated session identifier (UUID) used to route SSE events. | defaults to undefined|
| **lastEventID** | [**string**] | Resume SSE from a specific monotonic event id | (optional) defaults to undefined|


### Return type

**string**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/event-stream


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | text/event-stream |  * Content-Type -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

