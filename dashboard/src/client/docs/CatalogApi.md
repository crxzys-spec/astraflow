# CatalogApi

All URIs are relative to *https://scheduler.example.com*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**searchCatalogNodes**](#searchcatalognodes) | **GET** /api/v1/catalog/nodes/search | Search catalog nodes (system + worker capabilities)|

# **searchCatalogNodes**
> CatalogNodeSearchResponse searchCatalogNodes()


### Example

```typescript
import {
    CatalogApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CatalogApi(configuration);

let q: string; //Search text applied to node name, type, description, and tags. (default to undefined)
let _package: string; //Optional package filter derived from search results. (optional) (default to undefined)

const { status, data } = await apiInstance.searchCatalogNodes(
    q,
    _package
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **q** | [**string**] | Search text applied to node name, type, description, and tags. | defaults to undefined|
| **_package** | [**string**] | Optional package filter derived from search results. | (optional) defaults to undefined|


### Return type

**CatalogNodeSearchResponse**

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | OK |  -  |
|**400** | Invalid input |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

