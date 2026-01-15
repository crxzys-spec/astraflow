<template>
  <PublicLanding
    :packageTotalDisplay="libraryPackageTotalDisplay"
    :workflowTotalDisplay="libraryWorkflowTotalDisplay"
    v-model:searchQuery="librarySearchQuery"
    :tagFilter="libraryTagFilter"
    :topTags="topTags"
    :featuredPackages="featuredPackages"
    :featuredWorkflows="featuredWorkflows"
    :publicLoading="publicLoading"
    :publicError="publicError"
    :hasToken="hasToken"
    @open-auth="openAuthDialog"
    @open-console="openConsole"
    @apply-filters="applyPublicFilters"
    @reset-filters="resetPublicFilters"
    @select-tag="selectPublicTag"
    @open-package="openPackage"
    @open-workflow="openWorkflow"
  />
</template>

<script setup lang="ts">
import { inject, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PublicLanding from '../components/public/PublicLanding.vue'
import { hubStoreKey, useHubStore } from '../store/hubStore'
import type { PackageSummary, WorkflowSummary } from '../types/hub'

const hubStore = inject(hubStoreKey) ?? useHubStore()
const router = useRouter()
const {
  libraryPackageTotalDisplay,
  libraryWorkflowTotalDisplay,
  librarySearchQuery,
  libraryTagFilter,
  topTags,
  featuredPackages,
  featuredWorkflows,
  publicLoading,
  publicError,
  hasToken,
  openAuthDialog,
  applyLibraryFilters,
  resetLibraryFilters,
  selectPublicTag,
  loadLibrarySnapshot
} = hubStore

function applyPublicFilters() {
  applyLibraryFilters('snapshot')
}

function resetPublicFilters() {
  resetLibraryFilters('snapshot')
}

function openPackage(pkg: PackageSummary) {
  const owner = (pkg.ownerId || pkg.ownerName || '').trim()
  if (owner) {
    router.push(`/packages/${encodeURIComponent(owner)}/${encodeURIComponent(pkg.name)}`)
    return
  }
  router.push('/packages')
}

function openWorkflow(flow: WorkflowSummary) {
  router.push(`/workflows/${encodeURIComponent(flow.id)}`)
}

function openConsole() {
  router.push('/console/packages')
}

onMounted(() => {
  loadLibrarySnapshot()
})
</script>
