import type {
  AccountUpdateRequest,
  AccessTokenCreateRequest,
  OrganizationCreateRequest,
  OrganizationInviteCreateRequest,
  OrganizationMemberRequest,
  PackagePermissionCreateRequest,
  PackagePermissionUpdateRequest,
  WorkflowPermissionCreateRequest,
  WorkflowPermissionUpdateRequest
} from '../types/hub'
import { createHubApi } from '../api/hubApi'

export type HubApi = ReturnType<typeof createHubApi>

export function createHubService(api: HubApi) {
  return {
    fetchPublicSnapshot: async (query: string) => {
      const [packagesData, workflowsData] = await Promise.all([
        api.listPackages(query),
        api.listWorkflows(query)
      ])
      return {
        packagesData,
        workflowsData
      }
    },
    fetchPackages: (query: string) => api.listPackages(query),
    fetchWorkflows: (query: string) => api.listWorkflows(query),
    fetchPackageDetail: (name: string) => api.getPackage(name),
    deletePackage: (name: string) => api.deletePackage(name),
    fetchWorkflowDetail: (workflowId: string) => api.getWorkflow(workflowId),
    fetchWorkflowVersions: (workflowId: string) => api.listWorkflowVersions(workflowId),
    fetchWorkflowVersionDetail: (workflowId: string, versionId: string) =>
      api.getWorkflowVersion(workflowId, versionId),
    fetchOrganizations: () => api.listOrganizations(),
    createOrganization: (payload: OrganizationCreateRequest) => api.createOrganization(payload),
    updateOrganization: (orgId: string, payload: Record<string, string>) =>
      api.updateOrganization(orgId, payload),
    fetchOrganizationMembers: (orgId: string) => api.listOrganizationMembers(orgId),
    addOrganizationMember: (orgId: string, payload: OrganizationMemberRequest) =>
      api.addOrganizationMember(orgId, payload),
    removeOrganizationMember: (orgId: string, userId: string) =>
      api.removeOrganizationMember(orgId, userId),
    fetchAccountInvites: () => api.listAccountInvites(),
    fetchOrganizationInvites: (orgId: string) => api.listOrganizationInvites(orgId),
    createOrganizationInvite: (orgId: string, payload: OrganizationInviteCreateRequest) =>
      api.createOrganizationInvite(orgId, payload),
    revokeOrganizationInvite: (orgId: string, inviteId: string) =>
      api.revokeOrganizationInvite(orgId, inviteId),
    acceptOrganizationInvite: (orgId: string, inviteId: string) =>
      api.acceptOrganizationInvite(orgId, inviteId),
    declineOrganizationInvite: (orgId: string, inviteId: string) =>
      api.declineOrganizationInvite(orgId, inviteId),
    fetchWorkflowPermissions: (workflowId: string) => api.listWorkflowPermissions(workflowId),
    addWorkflowPermission: (workflowId: string, payload: WorkflowPermissionCreateRequest) =>
      api.addWorkflowPermission(workflowId, payload),
    updateWorkflowPermission: (
      workflowId: string,
      permissionId: string,
      payload: WorkflowPermissionUpdateRequest
    ) => api.updateWorkflowPermission(workflowId, permissionId, payload),
    deleteWorkflowPermission: (workflowId: string, permissionId: string) =>
      api.deleteWorkflowPermission(workflowId, permissionId),
    fetchPackagePermissions: (packageName: string) => api.listPackagePermissions(packageName),
    addPackagePermission: (packageName: string, payload: PackagePermissionCreateRequest) =>
      api.addPackagePermission(packageName, payload),
    updatePackagePermission: (
      packageName: string,
      permissionId: string,
      payload: PackagePermissionUpdateRequest
    ) => api.updatePackagePermission(packageName, permissionId, payload),
    deletePackagePermission: (packageName: string, permissionId: string) =>
      api.deletePackagePermission(packageName, permissionId),
    fetchAccount: () => api.getAccount(),
    updateAccount: (payload: AccountUpdateRequest) => api.updateAccount(payload),
    fetchTokens: () => api.listTokens(),
    createToken: (payload: AccessTokenCreateRequest) => api.createToken(payload),
    revokeToken: (tokenId: string) => api.revokeToken(tokenId)
  }
}
