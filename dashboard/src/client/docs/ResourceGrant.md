# ResourceGrant


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**grantId** | **string** |  | [default to undefined]
**resourceId** | **string** |  | [default to undefined]
**packageName** | **string** |  | [default to undefined]
**packageVersion** | **string** |  | [optional] [default to undefined]
**resourceKey** | **string** |  | [default to undefined]
**scope** | [**ResourceGrantScope**](ResourceGrantScope.md) |  | [default to undefined]
**workflowId** | **string** |  | [optional] [default to undefined]
**actions** | [**Array&lt;ResourceGrantAction&gt;**](ResourceGrantAction.md) |  | [default to undefined]
**createdAt** | **string** |  | [default to undefined]
**createdBy** | **string** |  | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** |  | [optional] [default to undefined]

## Example

```typescript
import { ResourceGrant } from './api';

const instance: ResourceGrant = {
    grantId,
    resourceId,
    packageName,
    packageVersion,
    resourceKey,
    scope,
    workflowId,
    actions,
    createdAt,
    createdBy,
    metadata,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
