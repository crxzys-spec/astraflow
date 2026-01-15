<template>
  <section class="workspace library-shell">
    <ResourceFilters
      title="Packages"
      subtitle="Browse public node packages published to the hub."
      v-model:searchQuery="librarySearchQuery"
      v-model:tagFilter="libraryTagFilter"
      v-model:ownerFilter="libraryOwnerFilter"
      @apply-filters="applyFilters"
      @reset-filters="resetFilters"
    />

    <el-alert
      v-if="libraryListError"
      class="hub-alert"
      type="error"
      show-icon
      :closable="false"
      :title="libraryListError"
    />

    <ResourceList
      resourceType="packages"
      :packages="libraryPackages"
      :workflows="[]"
      :loading="libraryListLoading"
      v-model:page="libraryPage"
      v-model:pageSize="libraryPageSize"
      :total="libraryPackageTotal || 0"
      emptyText="No public packages yet."
      @load-list="loadLibraryPackages"
      @handle-page-size="() => handleLibraryPageSize('packages')"
      @select-package="openPackage"
    />
  </section>
</template>

<script setup lang="ts">
import { inject, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ResourceFilters from '../components/library/ResourceFilters.vue'
import ResourceList from '../components/library/ResourceList.vue'
import { hubStoreKey, useHubStore } from '../store/hubStore'
import type { PackageSummary } from '../types/hub'

const hubStore = inject(hubStoreKey) ?? useHubStore()
const router = useRouter()

const {
  librarySearchQuery,
  libraryTagFilter,
  libraryOwnerFilter,
  libraryPage,
  libraryPageSize,
  libraryPackages,
  libraryPackageTotal,
  libraryListLoading,
  libraryListError,
  loadLibraryPackages,
  applyLibraryFilters,
  resetLibraryFilters,
  handleLibraryPageSize
} = hubStore

function openPackage(pkg: PackageSummary) {
  const owner = (pkg.ownerId || pkg.ownerName || '').trim()
  if (owner) {
    router.push(`/packages/${encodeURIComponent(owner)}/${encodeURIComponent(pkg.name)}`)
    return
  }
  router.push('/packages')
}

function applyFilters() {
  applyLibraryFilters('packages')
}

function resetFilters() {
  resetLibraryFilters('packages')
}

onMounted(() => {
  loadLibraryPackages()
})
</script>
