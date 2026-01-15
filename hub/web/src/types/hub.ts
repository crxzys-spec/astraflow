export interface PageMeta {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export interface AccountProfile {
  id: string
  username: string
  displayName?: string
  email?: string
}

export interface AccountUpdateRequest {
  displayName?: string
  email?: string
}

export type TokenScope = 'read' | 'publish' | 'admin'

export interface AccessToken {
  id: string
  label: string
  scopes: TokenScope[]
  packageName?: string
  orgId?: string
  createdAt?: string
  createdIp?: string
  createdUserAgent?: string
  lastUsedAt?: string
  lastUsedIp?: string
  lastUsedUserAgent?: string
  expiresAt?: string
  token?: string
}

export interface AccessTokenCreateRequest {
  label: string
  scopes: TokenScope[]
  packageName?: string
  orgId?: string
  expiresAt?: string
}

export interface AuthResponse {
  account: AccountProfile
  token: AccessToken
}

export interface PackageListResponse {
  items: PackageSummary[]
  meta: PageMeta
}

export interface WorkflowListResponse {
  items: WorkflowSummary[]
  meta: PageMeta
}

export interface WorkflowVersionList {
  items: WorkflowVersionSummary[]
}

export interface OrganizationListResponse {
  items: Organization[]
}

export type OrganizationInviteStatus =
  | 'pending'
  | 'accepted'
  | 'declined'
  | 'revoked'
  | 'expired'

export interface OrganizationInvite {
  id: string
  orgId: string
  invitedBy: string
  userId: string
  email?: string
  role: OrganizationMemberRole
  status: OrganizationInviteStatus
  createdAt?: string
  expiresAt?: string
  respondedAt?: string
}

export interface OrganizationInviteCreateRequest {
  userId: string
  role?: OrganizationMemberRole
  expiresAt?: string
}

export interface OrganizationInviteList {
  items: OrganizationInvite[]
}

export interface OrganizationMember {
  userId: string
  role: OrganizationMemberRole
  joinedAt?: string
}

export interface OrganizationMemberRequest {
  userId: string
  role: OrganizationMemberRole
}

export interface OrganizationMemberList {
  items: OrganizationMember[]
}

export interface PackageSummary {
  name: string
  latestVersion?: string
  description?: string
  tags?: string[]
  ownerName?: string
  visibility?: string
  updatedAt?: string
}

export interface PackageDetail {
  name: string
  description?: string
  readme?: string
  versions: string[]
  distTags?: Record<string, string>
  tags?: string[]
  ownerId?: string
  ownerName?: string
  updatedAt?: string
  visibility?: string
}

export interface WorkflowSummary {
  id: string
  name: string
  summary?: string
  description?: string
  tags?: string[]
  ownerName?: string
  updatedAt?: string
  latestVersion?: string
  visibility?: string
}

export interface WorkflowDetail {
  id: string
  name: string
  summary?: string
  description?: string
  tags?: string[]
  ownerId?: string
  ownerName?: string
  updatedAt?: string
  visibility?: string
  previewImage?: string
}

export interface WorkflowVersionSummary {
  id: string
  version: string
  publishedAt?: string
  changelog?: string
}

export interface PackageDependency {
  name: string
  version: string
}

export interface WorkflowVersionDetail {
  id: string
  version: string
  summary?: string
  description?: string
  tags?: string[]
  previewImage?: string
  dependencies?: PackageDependency[]
  publishedAt?: string
  publisherId?: string
}

export interface Organization {
  id: string
  name: string
  slug: string
  ownerId: string
  createdAt?: string
  updatedAt?: string
}

export interface OrganizationCreateRequest {
  name: string
  slug: string
}

export type OrganizationMemberRole = 'owner' | 'admin' | 'member'

export type WorkflowPermissionRole = 'owner' | 'write' | 'read'

export type WorkflowPermissionSubjectType = 'user' | 'org'

export interface WorkflowPermission {
  id: string
  workflowId: string
  subjectType: WorkflowPermissionSubjectType
  subjectId: string
  role: WorkflowPermissionRole
  createdAt?: string
}

export interface WorkflowPermissionCreateRequest {
  subjectType: WorkflowPermissionSubjectType
  subjectId: string
  role: WorkflowPermissionRole
}

export interface WorkflowPermissionUpdateRequest {
  role: WorkflowPermissionRole
}

export interface WorkflowPermissionList {
  items: WorkflowPermission[]
}

export type PackagePermissionRole = 'owner' | 'write' | 'read'

export type PackagePermissionSubjectType = 'user' | 'org'

export interface PackagePermission {
  id: string
  packageName: string
  subjectType: PackagePermissionSubjectType
  subjectId: string
  role: PackagePermissionRole
  createdAt?: string
}

export interface PackagePermissionCreateRequest {
  subjectType: PackagePermissionSubjectType
  subjectId: string
  role: PackagePermissionRole
}

export interface PackagePermissionUpdateRequest {
  role: PackagePermissionRole
}

export interface PackagePermissionList {
  items: PackagePermission[]
}

export type HubTab = 'packages' | 'workflows' | 'orgs' | 'profile' | 'keys' | 'devices'
