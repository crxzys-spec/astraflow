<template>
  <ConsoleStatus
    :packageTotalDisplay="packageTotalDisplay"
    :workflowTotalDisplay="workflowTotalDisplay"
    :hasToken="hasToken"
  />

  <section class="console-shell">
    <aside class="console-nav">
      <div class="console-nav-title">Console</div>
      <div class="console-nav-group">
        <button
          class="console-nav-item"
          :class="{ 'console-nav-item--active': activeTab === 'packages' }"
          type="button"
          @click="navigateSection('packages')"
        >
          Packages
        </button>
        <button
          class="console-nav-item"
          :class="{ 'console-nav-item--active': activeTab === 'workflows' }"
          type="button"
          @click="navigateSection('workflows')"
        >
          Workflows
        </button>
        <button
          class="console-nav-item"
          :class="{ 'console-nav-item--active': activeTab === 'orgs' }"
          type="button"
          @click="navigateSection('orgs')"
        >
          Organizations
        </button>
        <button
          class="console-nav-item"
          :class="{ 'console-nav-item--active': activeTab === 'profile' }"
          type="button"
          @click="navigateSection('profile')"
        >
          Profile
        </button>
        <button
          class="console-nav-item"
          :class="{ 'console-nav-item--active': activeTab === 'keys' }"
          type="button"
          @click="navigateSection('keys')"
        >
          API keys
        </button>
        <button
          class="console-nav-item"
          :class="{ 'console-nav-item--active': activeTab === 'devices' }"
          type="button"
          @click="navigateSection('devices')"
        >
          Sessions
        </button>
      </div>
    </aside>

    <div class="workspace">
      <ConsoleToolbar
        :activeTab="activeTab"
      v-model:searchQuery="searchQuery"
      v-model:tagFilter="tagFilter"
      v-model:ownerFilter="ownerFilter"
      @apply-filters="applyConsoleFilters"
      @reset-filters="resetConsoleFilters"
      @open-org-create="openOrgCreate"
    />

      <el-alert
        v-if="listError && activeTab !== 'profile' && activeTab !== 'keys' && activeTab !== 'devices'"
        class="hub-alert"
        type="error"
        show-icon
        :closable="false"
        :title="listError"
      />

      <AccountPanel
        v-if="activeTab === 'profile' || activeTab === 'keys' || activeTab === 'devices'"
        :account="accountProfile"
        :accountLoading="accountLoading"
        :accountError="accountError"
        :accountInvites="accountInvites"
        :accountInvitesLoading="accountInvitesLoading"
        :accountInvitesError="accountInvitesError"
        :accountEditForm="accountEditForm"
        :accountEditLoading="accountEditLoading"
        :accountEditError="accountEditError"
        :tokens="tokens"
        :tokensLoading="tokensLoading"
        :tokensError="tokensError"
        :tokenCreateLoading="tokenCreateLoading"
        :tokenCreateError="tokenCreateError"
        :tokenCreateResult="tokenCreateResult"
        :currentTokenId="authTokenId"
        :orgOptions="orgOptions"
        :orgOptionsLoading="orgOptionsLoading"
        :orgOptionsError="orgOptionsError"
        :mode="accountMode"
        @create-token="createToken"
        @revoke-token="revokeToken"
        @clear-created-token="clearCreatedToken"
        @accept-org-invite="acceptOrgInvite"
        @decline-org-invite="declineOrgInvite"
        @update-account="updateAccountProfile"
        @reset-account-edit="resetAccountEditForm"
      />

      <div v-else class="workspace-body">
        <ConsoleList
          v-model:page="page"
          v-model:pageSize="pageSize"
          :activeTab="activeTab"
          :listLoading="listLoading"
          :packages="packages"
          :workflows="workflows"
          :organizations="organizations"
          :hasListData="hasListData"
          :activeTotal="activeTotal"
          @load-list="loadList"
          @handle-page-size="handlePageSize"
          @select-package="selectPackage"
          @select-workflow="selectWorkflow"
          @select-organization="selectOrganization"
          @open-org-edit="openOrgEdit"
        />

        <ConsoleDetail
          :detailTitle="detailTitle"
          :detailLoading="detailLoading"
          :detailError="detailError"
          :selectedPackage="selectedPackage"
          :selectedWorkflow="selectedWorkflow"
          :selectedOrg="selectedOrg"
          :workflowVersions="workflowVersions"
          :selectedWorkflowVersion="selectedWorkflowVersion"
          :workflowVersionLoading="workflowVersionLoading"
          :workflowVersionError="workflowVersionError"
          :workflowDependencies="workflowDependencies"
          :packagePermissions="packagePermissions"
          :packagePermissionsLoading="packagePermissionsLoading"
          :packagePermissionsError="packagePermissionsError"
          :workflowPermissions="workflowPermissions"
          :workflowPermissionsLoading="workflowPermissionsLoading"
          :workflowPermissionsError="workflowPermissionsError"
          :orgInvites="orgInvites"
          :orgInvitesLoading="orgInvitesLoading"
          :orgInvitesError="orgInvitesError"
          :orgMembers="orgMembers"
          :orgMembersLoading="orgMembersLoading"
          :orgMembersError="orgMembersError"
          :workflowPreviewSrc="workflowPreviewSrc"
          @clear-selection="clearSelection"
          @select-workflow-version="selectWorkflowVersion"
          @open-org-invite="openOrgInvite"
          @revoke-org-invite="handleRevokeOrgInvite"
          @update-org-member="handleUpdateOrgMember"
          @remove-org-member="handleRemoveOrgMember"
          @add-workflow-permission="handleAddWorkflowPermission"
          @update-workflow-permission="handleUpdateWorkflowPermission"
          @delete-workflow-permission="handleDeleteWorkflowPermission"
          @add-package-permission="handleAddPackagePermission"
          @update-package-permission="handleUpdatePackagePermission"
          @delete-package-permission="handleDeletePackagePermission"
          @delete-package="handleDeletePackage"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, inject, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AccountPanel from '../components/AccountPanel.vue'
import ConsoleDetail from '../components/console/ConsoleDetail.vue'
import ConsoleList from '../components/console/ConsoleList.vue'
import ConsoleStatus from '../components/console/ConsoleStatus.vue'
import ConsoleToolbar from '../components/console/ConsoleToolbar.vue'
import { hubStoreKey, useHubStore } from '../store/hubStore'
import type {
  HubTab,
  OrganizationInvite,
  OrganizationMember,
  OrganizationMemberRole,
  PackagePermission,
  PackagePermissionCreateRequest,
  PackagePermissionRole,
  WorkflowPermission,
  WorkflowPermissionCreateRequest,
  WorkflowPermissionRole
} from '../types/hub'

const hubStore = inject(hubStoreKey) ?? useHubStore()
const route = useRoute()
const router = useRouter()
const {
  activeTab,
  searchQuery,
  tagFilter,
  ownerFilter,
  page,
  pageSize,
  listLoading,
  listError,
  packages,
  workflows,
  organizations,
  activeTotal,
  hasListData,
  packageTotalDisplay,
  workflowTotalDisplay,
  detailTitle,
  detailLoading,
  detailError,
  selectedPackage,
  selectedWorkflow,
  selectedOrg,
  workflowVersions,
  selectedWorkflowVersion,
  workflowVersionLoading,
  workflowVersionError,
  workflowDependencies,
  packagePermissions,
  packagePermissionsLoading,
  packagePermissionsError,
  workflowPermissions,
  workflowPermissionsLoading,
  workflowPermissionsError,
  orgInvites,
  orgInvitesLoading,
  orgInvitesError,
  orgMembers,
  orgMembersLoading,
  orgMembersError,
  workflowPreviewSrc,
  resolvePackageRef,
  hasToken,
  accountProfile,
  accountLoading,
  accountError,
  accountInvites,
  accountInvitesLoading,
  accountInvitesError,
  accountEditForm,
  accountEditLoading,
  accountEditError,
  tokens,
  tokensLoading,
  tokensError,
  tokenCreateLoading,
  tokenCreateError,
  tokenCreateResult,
  authTokenId,
  orgOptions,
  orgOptionsLoading,
  orgOptionsError,
  applyConsoleFilters,
  resetConsoleFilters,
  loadList,
  handlePageSize,
  selectPackage,
  selectWorkflow,
  selectOrganization,
  clearSelection,
  selectWorkflowVersion,
  openOrgCreate,
  openOrgEdit,
  openOrgInvite,
  createToken,
  revokeOrgInvite,
  revokeToken,
  clearCreatedToken,
  acceptOrgInvite,
  declineOrgInvite,
  addWorkflowPermission,
  updateWorkflowPermission,
  deleteWorkflowPermission,
  addPackagePermission,
  updatePackagePermission,
  deletePackagePermission,
  deletePackage,
  updateOrgMemberRole,
  removeOrgMember,
  updateAccountProfile,
  resetAccountEditForm
} = hubStore

const currentSection = computed<HubTab>(() => {
  const section = route.params.section
  if (section === 'workflows'
    || section === 'orgs'
    || section === 'profile'
    || section === 'keys'
    || section === 'devices'
    || section === 'packages') {
    return section
  }
  return 'packages'
})

const accountMode = computed(() => {
  if (activeTab.value === 'keys') return 'keys'
  if (activeTab.value === 'devices') return 'devices'
  return 'profile'
})

watch(
  () => currentSection.value,
  (section) => {
    if (activeTab.value !== section) {
      activeTab.value = section
    }
  },
  { immediate: true }
)

function navigateSection(section: HubTab) {
  if (activeTab.value !== section) {
    activeTab.value = section
  }
  const target = `/console/${section}`
  if (router.currentRoute.value.path !== target) {
    router.push(target)
  }
}

function handleRevokeOrgInvite(invite: OrganizationInvite) {
  if (!selectedOrg.value) {
    return
  }
  revokeOrgInvite(selectedOrg.value.id, invite.id)
}

function handleAddWorkflowPermission(payload: WorkflowPermissionCreateRequest) {
  if (!selectedWorkflow.value) {
    return
  }
  addWorkflowPermission(selectedWorkflow.value.id, payload)
}

function handleUpdateWorkflowPermission(permission: WorkflowPermission, role: WorkflowPermissionRole) {
  if (!selectedWorkflow.value) {
    return
  }
  updateWorkflowPermission(selectedWorkflow.value.id, permission.id, { role })
}

function handleDeleteWorkflowPermission(permission: WorkflowPermission) {
  if (!selectedWorkflow.value) {
    return
  }
  deleteWorkflowPermission(selectedWorkflow.value.id, permission.id)
}

function handleUpdateOrgMember(member: OrganizationMember, role: OrganizationMemberRole) {
  if (!selectedOrg.value) {
    return
  }
  updateOrgMemberRole(selectedOrg.value.id, member.userId, role)
}

function handleRemoveOrgMember(member: OrganizationMember) {
  if (!selectedOrg.value) {
    return
  }
  removeOrgMember(selectedOrg.value.id, member.userId)
}

function handleAddPackagePermission(payload: PackagePermissionCreateRequest) {
  if (!selectedPackage.value) {
    return
  }
  addPackagePermission(resolvePackageRef(selectedPackage.value), payload)
}

function handleUpdatePackagePermission(permission: PackagePermission, role: PackagePermissionRole) {
  if (!selectedPackage.value) {
    return
  }
  updatePackagePermission(resolvePackageRef(selectedPackage.value), permission.id, { role })
}

function handleDeletePackagePermission(permission: PackagePermission) {
  if (!selectedPackage.value) {
    return
  }
  deletePackagePermission(resolvePackageRef(selectedPackage.value), permission.id)
}

function handleDeletePackage(pkg: { name?: string | null; ownerId?: string | null; ownerName?: string | null }) {
  const ref = resolvePackageRef(pkg)
  if (!ref) {
    return
  }
  deletePackage(ref)
}
</script>
