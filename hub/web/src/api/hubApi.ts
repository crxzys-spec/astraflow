import type { HubClient } from '../client/hubClient'
import type {
  AccessToken,
  AccessTokenCreateRequest,
  AccountProfile,
  AccountUpdateRequest,
  AuthResponse,
  OrganizationCreateRequest,
  Organization,
  OrganizationInvite,
  OrganizationInviteCreateRequest,
  OrganizationInviteList,
  OrganizationMember,
  OrganizationMemberList,
  OrganizationMemberRequest,
  PackageDetail,
  PackageListResponse,
  PackagePermission,
  PackagePermissionCreateRequest,
  PackagePermissionList,
  PackagePermissionUpdateRequest,
  WorkflowDetail,
  WorkflowListResponse,
  WorkflowPermission,
  WorkflowPermissionCreateRequest,
  WorkflowPermissionList,
  WorkflowPermissionUpdateRequest,
  WorkflowVersionDetail,
  WorkflowVersionList
} from '../types/hub'

const splitPackageRef = (ref: string) => {
  const trimmed = ref.trim()
  if (!trimmed) return { owner: '', name: '' }
  const [owner, ...rest] = trimmed.split('/')
  if (rest.length === 0) {
    return { owner: '', name: trimmed }
  }
  return { owner: owner.trim(), name: rest.join('/').trim() }
}

const buildPackagePath = (ref: string, suffix = '') => {
  const { owner, name } = splitPackageRef(ref)
  if (owner) {
    return `/api/v1/packages/${encodeURIComponent(owner)}/${encodeURIComponent(name)}${suffix}`
  }
  return `/api/v1/packages/${encodeURIComponent(name)}${suffix}`
}

export function createHubApi(client: HubClient) {
  return {
    login: (payload: Record<string, unknown>) =>
      client.requestAuth<AuthResponse>('/api/v1/auth/login', payload),
    register: (payload: Record<string, unknown>) =>
      client.requestAuth<AuthResponse>('/api/v1/auth/register', payload),
    listPackages: (query: string) =>
      client.requestJson<PackageListResponse>(`/api/v1/packages?${query}`),
    listWorkflows: (query: string) =>
      client.requestJson<WorkflowListResponse>(`/api/v1/workflows?${query}`),
    getPackage: (name: string) =>
      client.requestJson<PackageDetail>(buildPackagePath(name)),
    deletePackage: (name: string) =>
      client.requestJson<null>(
        buildPackagePath(name),
        { method: 'DELETE' },
        true
      ),
    getWorkflow: (workflowId: string) =>
      client.requestJson<WorkflowDetail>(`/api/v1/workflows/${encodeURIComponent(workflowId)}`),
    listWorkflowVersions: (workflowId: string) =>
      client.requestJson<WorkflowVersionList>(
        `/api/v1/workflows/${encodeURIComponent(workflowId)}/versions`
      ),
    getWorkflowVersion: (workflowId: string, versionId: string) =>
      client.requestJson<WorkflowVersionDetail>(
        `/api/v1/workflows/${encodeURIComponent(workflowId)}/versions/${encodeURIComponent(versionId)}`
      ),
    listOrganizations: () =>
      client.requestJson<{ items: Organization[] }>('/api/v1/orgs', {}, true),
    createOrganization: (payload: OrganizationCreateRequest) =>
      client.requestJson<Organization>(
        '/api/v1/orgs',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        },
        true
      ),
    addOrganizationMember: (orgId: string, payload: OrganizationMemberRequest) =>
      client.requestJson<OrganizationMember>(
        `/api/v1/orgs/${encodeURIComponent(orgId)}/members`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        },
        true
      ),
    removeOrganizationMember: (orgId: string, userId: string) =>
      client.requestJson<null>(
        `/api/v1/orgs/${encodeURIComponent(orgId)}/members/${encodeURIComponent(userId)}`,
        { method: 'DELETE' },
        true
      ),
    listAccountInvites: () =>
      client.requestJson<OrganizationInviteList>('/api/v1/account/invites', {}, true),
    listOrganizationInvites: (orgId: string) =>
      client.requestJson<OrganizationInviteList>(
        `/api/v1/orgs/${encodeURIComponent(orgId)}/invites`,
        {},
        true
      ),
    listOrganizationMembers: (orgId: string) =>
      client.requestJson<OrganizationMemberList>(
        `/api/v1/orgs/${encodeURIComponent(orgId)}/members`,
        {},
        true
      ),
    createOrganizationInvite: (orgId: string, payload: OrganizationInviteCreateRequest) =>
      client.requestJson<OrganizationInvite>(
        `/api/v1/orgs/${encodeURIComponent(orgId)}/invites`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        },
        true
      ),
    revokeOrganizationInvite: (orgId: string, inviteId: string) =>
      client.requestJson<null>(
        `/api/v1/orgs/${encodeURIComponent(orgId)}/invites/${encodeURIComponent(inviteId)}`,
        { method: 'DELETE' },
        true
      ),
    acceptOrganizationInvite: (orgId: string, inviteId: string) =>
      client.requestJson<OrganizationMember>(
        `/api/v1/orgs/${encodeURIComponent(orgId)}/invites/${encodeURIComponent(inviteId)}/accept`,
        { method: 'POST' },
        true
      ),
    declineOrganizationInvite: (orgId: string, inviteId: string) =>
      client.requestJson<null>(
        `/api/v1/orgs/${encodeURIComponent(orgId)}/invites/${encodeURIComponent(inviteId)}/decline`,
        { method: 'POST' },
        true
      ),
    updateOrganization: (orgId: string, payload: Record<string, string>) =>
      client.requestJson<Organization>(
        `/api/v1/orgs/${encodeURIComponent(orgId)}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        },
        true
      ),
    getAccount: () =>
      client.requestJson<AccountProfile>('/api/v1/account', {}, true),
    updateAccount: (payload: AccountUpdateRequest) =>
      client.requestJson<AccountProfile>(
        '/api/v1/account',
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        },
        true
      ),
    listTokens: () =>
      client.requestJson<{ items: AccessToken[] }>('/api/v1/tokens', {}, true),
    createToken: (payload: AccessTokenCreateRequest) =>
      client.requestJson<AccessToken>(
        '/api/v1/tokens/publish',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        },
        true
      ),
    revokeToken: (tokenId: string) =>
      client.requestJson<null>(
        `/api/v1/tokens/${encodeURIComponent(tokenId)}`,
        { method: 'DELETE' },
        true
      ),
    listWorkflowPermissions: (workflowId: string) =>
      client.requestJson<WorkflowPermissionList>(
        `/api/v1/workflows/${encodeURIComponent(workflowId)}/permissions`,
        {},
        true
      ),
    addWorkflowPermission: (
      workflowId: string,
      payload: WorkflowPermissionCreateRequest
    ) =>
      client.requestJson<WorkflowPermission>(
        `/api/v1/workflows/${encodeURIComponent(workflowId)}/permissions`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        },
        true
      ),
    updateWorkflowPermission: (
      workflowId: string,
      permissionId: string,
      payload: WorkflowPermissionUpdateRequest
    ) =>
      client.requestJson<WorkflowPermission>(
        `/api/v1/workflows/${encodeURIComponent(workflowId)}/permissions/${encodeURIComponent(permissionId)}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        },
        true
      ),
    deleteWorkflowPermission: (workflowId: string, permissionId: string) =>
      client.requestJson<null>(
        `/api/v1/workflows/${encodeURIComponent(workflowId)}/permissions/${encodeURIComponent(permissionId)}`,
        { method: 'DELETE' },
        true
      ),
    listPackagePermissions: (packageName: string) =>
      client.requestJson<PackagePermissionList>(
        buildPackagePath(packageName, '/permissions'),
        {},
        true
      ),
    addPackagePermission: (packageName: string, payload: PackagePermissionCreateRequest) =>
      client.requestJson<PackagePermission>(
        buildPackagePath(packageName, '/permissions'),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        },
        true
      ),
    updatePackagePermission: (
      packageName: string,
      permissionId: string,
      payload: PackagePermissionUpdateRequest
    ) =>
      client.requestJson<PackagePermission>(
        buildPackagePath(
          packageName,
          `/permissions/${encodeURIComponent(permissionId)}`
        ),
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        },
        true
      ),
    deletePackagePermission: (packageName: string, permissionId: string) =>
      client.requestJson<null>(
        buildPackagePath(
          packageName,
          `/permissions/${encodeURIComponent(permissionId)}`
        ),
        { method: 'DELETE' },
        true
      )
  }
}
