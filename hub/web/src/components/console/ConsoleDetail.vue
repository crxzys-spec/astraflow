<template>
  <aside class="detail-pane">
    <div class="detail-card">
      <div class="detail-header">
        <div>
          <div class="detail-eyebrow">Details</div>
          <h3>{{ detailTitle }}</h3>
        </div>
        <el-button
          v-if="detailTitle !== 'Select an item'"
          size="small"
          plain
          @click="clearSelection"
        >
          Clear
        </el-button>
      </div>

      <el-skeleton v-if="detailLoading" animated :rows="8" />
      <el-alert
        v-else-if="detailError"
        type="error"
        show-icon
        :closable="false"
        :title="detailError"
      />
      <template v-else-if="selectedPackage">
        <PackageDetail :pkg="selectedPackage" />
        <div class="detail-section permission-section">
          <div class="section-header">
            <div class="section-title">Access</div>
          </div>
          <el-skeleton v-if="packagePermissionsLoading" animated :rows="4" />
          <el-alert
            v-else-if="packagePermissionsError"
            type="error"
            show-icon
            :closable="false"
            :title="packagePermissionsError"
          />
          <div v-else class="detail-list">
            <div v-if="packagePermissions.length === 0" class="detail-empty">
              No access rules configured.
            </div>
            <div v-else class="detail-list">
              <div v-for="permission in packagePermissions" :key="permission.id" class="detail-row">
                <div class="detail-row__main">
                  <div class="detail-row__title">
                    {{ permission.subjectType.toUpperCase() }} · {{ permission.subjectId }}
                  </div>
                  <div class="detail-row__meta">
                    Added {{ formatDate(permission.createdAt) }}
                  </div>
                </div>
                <div class="detail-row__actions">
                  <el-select
                    size="small"
                    :model-value="permission.role"
                    :disabled="permission.role === 'owner'"
                    @change="(role) => updatePackagePermissionRole(permission, role)"
                  >
                    <el-option label="Owner" value="owner" />
                    <el-option label="Write" value="write" />
                    <el-option label="Read" value="read" />
                  </el-select>
                  <el-button
                    size="small"
                    plain
                    :disabled="permission.role === 'owner'"
                    @click="removePackagePermission(permission)"
                  >
                    Remove
                  </el-button>
                </div>
              </div>
            </div>
          </div>
          <div class="permission-form">
            <div class="permission-form__title">Add access</div>
            <div class="permission-form__grid">
              <el-select v-model="packagePermissionForm.subjectType" size="small">
                <el-option label="User" value="user" />
                <el-option label="Organization" value="org" />
              </el-select>
              <el-input
                v-model="packagePermissionForm.subjectId"
                size="small"
                placeholder="user id or org slug"
              />
              <el-select v-model="packagePermissionForm.role" size="small">
                <el-option label="Read" value="read" />
                <el-option label="Write" value="write" />
              </el-select>
              <el-button size="small" type="primary" @click="submitPackagePermission">
                Add
              </el-button>
            </div>
            <el-alert
              v-if="packagePermissionError"
              type="error"
              show-icon
              :closable="false"
              :title="packagePermissionError"
            />
          </div>
        </div>
        <div class="detail-section danger-section">
          <div class="section-header">
            <div class="section-title">Danger zone</div>
          </div>
          <div class="detail-row">
            <div class="detail-row__main">
              <div class="detail-row__title">Delete package</div>
              <div class="detail-row__meta">
                Removes all published versions and archive files.
              </div>
            </div>
            <div class="detail-row__actions">
              <el-button size="small" type="danger" @click="deleteSelectedPackage">
                Delete
              </el-button>
            </div>
          </div>
        </div>
      </template>

      <template v-else-if="selectedWorkflow">
        <WorkflowDetail
          :workflow="selectedWorkflow"
          :previewSrc="workflowPreviewSrc"
          :versions="workflowVersions"
          :selectedVersion="selectedWorkflowVersion"
          :versionLoading="workflowVersionLoading"
          :versionError="workflowVersionError"
          :dependencies="workflowDependencies"
          @select-version="selectWorkflowVersion"
        />
        <div class="detail-section permission-section">
          <div class="section-header">
            <div class="section-title">Access</div>
          </div>
          <el-skeleton v-if="workflowPermissionsLoading" animated :rows="4" />
          <el-alert
            v-else-if="workflowPermissionsError"
            type="error"
            show-icon
            :closable="false"
            :title="workflowPermissionsError"
          />
          <div v-else class="detail-list">
            <div v-if="workflowPermissions.length === 0" class="detail-empty">
              No access rules configured.
            </div>
            <div v-else class="detail-list">
              <div v-for="permission in workflowPermissions" :key="permission.id" class="detail-row">
                <div class="detail-row__main">
                  <div class="detail-row__title">
                    {{ permission.subjectType.toUpperCase() }} · {{ permission.subjectId }}
                  </div>
                  <div class="detail-row__meta">
                    Added {{ formatDate(permission.createdAt) }}
                  </div>
                </div>
                <div class="detail-row__actions">
                  <el-select
                    size="small"
                    :model-value="permission.role"
                    :disabled="permission.role === 'owner'"
                    @change="(role) => updatePermissionRole(permission, role)"
                  >
                    <el-option label="Owner" value="owner" />
                    <el-option label="Write" value="write" />
                    <el-option label="Read" value="read" />
                  </el-select>
                  <el-button
                    size="small"
                    plain
                    :disabled="permission.role === 'owner'"
                    @click="removePermission(permission)"
                  >
                    Remove
                  </el-button>
                </div>
              </div>
            </div>
          </div>
          <div class="permission-form">
            <div class="permission-form__title">Add access</div>
            <div class="permission-form__grid">
              <el-select v-model="permissionForm.subjectType" size="small">
                <el-option label="User" value="user" />
                <el-option label="Organization" value="org" />
              </el-select>
              <el-input
                v-model="permissionForm.subjectId"
                size="small"
                placeholder="user id or org slug"
              />
              <el-select v-model="permissionForm.role" size="small">
                <el-option label="Read" value="read" />
                <el-option label="Write" value="write" />
              </el-select>
              <el-button size="small" type="primary" @click="submitPermission">
                Add
              </el-button>
            </div>
            <el-alert
              v-if="permissionError"
              type="error"
              show-icon
              :closable="false"
              :title="permissionError"
            />
          </div>
        </div>
      </template>

      <div v-else-if="selectedOrg" class="detail-body">
        <div class="detail-meta">
          <div>
            <span class="meta-label">Owner</span>
            <span>{{ selectedOrg.ownerId }}</span>
          </div>
          <div>
            <span class="meta-label">Slug</span>
            <span>{{ selectedOrg.slug }}</span>
          </div>
          <div>
            <span class="meta-label">Updated</span>
            <span>{{ formatDate(selectedOrg.updatedAt) }}</span>
          </div>
        </div>
        <div class="detail-section">
          <div class="section-header">
            <div class="section-title">Members</div>
            <span class="section-count">{{ orgMembers.length }}</span>
          </div>
          <el-skeleton v-if="orgMembersLoading" animated :rows="4" />
          <el-alert
            v-else-if="orgMembersError"
            type="error"
            show-icon
            :closable="false"
            :title="orgMembersError"
          />
          <div v-else class="detail-list">
            <div v-if="orgMembers.length === 0" class="detail-empty">
              No members yet.
            </div>
            <div v-else class="detail-list">
              <div v-for="member in orgMembers" :key="member.userId" class="detail-row">
                <div class="detail-row__main">
                  <div class="detail-row__title">{{ member.userId }}</div>
                  <div class="detail-row__meta">
                    Joined {{ formatDate(member.joinedAt) }}
                  </div>
                </div>
                <div class="detail-row__actions">
                  <el-select
                    size="small"
                    :model-value="member.role"
                    :disabled="member.role === 'owner'"
                    @change="(role) => updateOrgMemberRole(member, role)"
                  >
                    <el-option label="Owner" value="owner" />
                    <el-option label="Admin" value="admin" />
                    <el-option label="Member" value="member" />
                  </el-select>
                  <el-button
                    size="small"
                    plain
                    :disabled="member.role === 'owner'"
                    @click="removeOrgMember(member)"
                  >
                    Remove
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="detail-section">
          <div class="section-header">
            <div class="section-title">Invites</div>
            <el-button size="small" plain @click="openOrgInvite">Invite member</el-button>
          </div>
          <el-skeleton v-if="orgInvitesLoading" animated :rows="4" />
          <el-alert
            v-else-if="orgInvitesError"
            type="error"
            show-icon
            :closable="false"
            :title="orgInvitesError"
          />
          <div v-else class="detail-list">
            <div v-if="orgInvites.length === 0" class="detail-empty">
              No invites yet.
            </div>
            <div v-else class="detail-list">
              <div v-for="invite in orgInvites" :key="invite.id" class="detail-row">
                <div class="detail-row__main">
                  <div class="detail-row__title">{{ invite.email || invite.userId }}</div>
                  <div class="detail-row__meta">
                    Role {{ invite.role }} · Sent {{ formatDate(invite.createdAt) }} · By {{ invite.invitedBy }}
                  </div>
                </div>
                <div class="detail-row__actions">
                  <span class="detail-chip" :class="statusClass(invite.status)">
                    {{ invite.status }}
                  </span>
                  <el-button
                    v-if="invite.status === 'pending'"
                    size="small"
                    plain
                    @click="revokeInvite(invite)"
                  >
                    Revoke
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="detail-empty">
        <p>Select a package, workflow, or organization to see details.</p>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import PackageDetail from '../library/PackageDetail.vue'
import WorkflowDetail from '../library/WorkflowDetail.vue'
import type {
  Organization,
  OrganizationInvite,
  OrganizationMember,
  PackageDetail as PackageDetailModel,
  PackagePermission,
  PackagePermissionCreateRequest,
  PackagePermissionRole,
  WorkflowDetail as WorkflowDetailModel,
  WorkflowPermission,
  WorkflowPermissionCreateRequest,
  WorkflowPermissionRole,
  WorkflowVersionDetail,
  WorkflowVersionSummary
} from '../../types/hub'

const props = defineProps<{
  detailTitle: string
  detailLoading: boolean
  detailError: string
  selectedPackage: PackageDetailModel | null
  selectedWorkflow: WorkflowDetailModel | null
  selectedOrg: Organization | null
  workflowVersions: WorkflowVersionSummary[]
  selectedWorkflowVersion: WorkflowVersionDetail | null
  workflowVersionLoading: boolean
  workflowVersionError: string
  workflowDependencies: { name: string; version: string }[]
  packagePermissions: PackagePermission[]
  packagePermissionsLoading: boolean
  packagePermissionsError: string
  workflowPermissions: WorkflowPermission[]
  workflowPermissionsLoading: boolean
  workflowPermissionsError: string
  orgInvites: OrganizationInvite[]
  orgInvitesLoading: boolean
  orgInvitesError: string
  orgMembers: OrganizationMember[]
  orgMembersLoading: boolean
  orgMembersError: string
  workflowPreviewSrc: string
}>()

const emit = defineEmits<{
  (e: 'clear-selection'): void
  (e: 'select-workflow-version', ver: WorkflowVersionSummary): void
  (e: 'open-org-invite'): void
  (e: 'revoke-org-invite', invite: OrganizationInvite): void
  (e: 'update-org-member', member: OrganizationMember, role: OrganizationMember['role']): void
  (e: 'remove-org-member', member: OrganizationMember): void
  (e: 'add-workflow-permission', payload: WorkflowPermissionCreateRequest): void
  (e: 'update-workflow-permission', permission: WorkflowPermission, role: WorkflowPermissionRole): void
  (e: 'delete-workflow-permission', permission: WorkflowPermission): void
  (e: 'add-package-permission', payload: PackagePermissionCreateRequest): void
  (e: 'update-package-permission', permission: PackagePermission, role: PackagePermissionRole): void
  (e: 'delete-package-permission', permission: PackagePermission): void
  (e: 'delete-package', pkg: PackageDetailModel): void
}>()

function clearSelection() {
  emit('clear-selection')
}

function selectWorkflowVersion(ver: WorkflowVersionSummary) {
  emit('select-workflow-version', ver)
}

function openOrgInvite() {
  emit('open-org-invite')
}

function revokeInvite(invite: OrganizationInvite) {
  emit('revoke-org-invite', invite)
}

function updateOrgMemberRole(member: OrganizationMember, role: OrganizationMember['role']) {
  emit('update-org-member', member, role)
}

function removeOrgMember(member: OrganizationMember) {
  emit('remove-org-member', member)
}

const permissionForm = reactive<WorkflowPermissionCreateRequest>({
  subjectType: 'user',
  subjectId: '',
  role: 'read'
})
const permissionError = ref('')

const packagePermissionForm = reactive<PackagePermissionCreateRequest>({
  subjectType: 'user',
  subjectId: '',
  role: 'read'
})
const packagePermissionError = ref('')

function submitPermission() {
  permissionError.value = ''
  const subjectId = permissionForm.subjectId.trim()
  if (!subjectId) {
    permissionError.value = 'Subject ID is required.'
    return
  }
  emit('add-workflow-permission', {
    subjectType: permissionForm.subjectType,
    subjectId,
    role: permissionForm.role
  })
  permissionForm.subjectId = ''
  permissionForm.role = 'read'
}

function submitPackagePermission() {
  packagePermissionError.value = ''
  const subjectId = packagePermissionForm.subjectId.trim()
  if (!subjectId) {
    packagePermissionError.value = 'Subject ID is required.'
    return
  }
  emit('add-package-permission', {
    subjectType: packagePermissionForm.subjectType,
    subjectId,
    role: packagePermissionForm.role
  })
  packagePermissionForm.subjectId = ''
  packagePermissionForm.role = 'read'
}

function updatePermissionRole(permission: WorkflowPermission, role: WorkflowPermissionRole) {
  if (permission.role === role) {
    return
  }
  emit('update-workflow-permission', permission, role)
}

function updatePackagePermissionRole(permission: PackagePermission, role: PackagePermissionRole) {
  if (permission.role === role) {
    return
  }
  emit('update-package-permission', permission, role)
}

function removePermission(permission: WorkflowPermission) {
  emit('delete-workflow-permission', permission)
}

function removePackagePermission(permission: PackagePermission) {
  emit('delete-package-permission', permission)
}

function deleteSelectedPackage() {
  if (!props.selectedPackage) {
    return
  }
  emit('delete-package', props.selectedPackage)
}

function statusClass(status: OrganizationInvite['status']) {
  return `detail-chip--${status}`
}

function formatDate(value?: string) {
  if (!value) return 'Unknown'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unknown'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric'
  }).format(date)
}
</script>
