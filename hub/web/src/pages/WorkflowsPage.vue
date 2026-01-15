<template>
  <section class="workspace library-shell">
    <ResourceFilters
      title="Workflows"
      subtitle="Discover reusable workflows published to the hub."
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
      resourceType="workflows"
      :packages="[]"
      :workflows="libraryWorkflows"
      :loading="libraryListLoading"
      v-model:page="libraryPage"
      v-model:pageSize="libraryPageSize"
      :total="libraryWorkflowTotal || 0"
      emptyText="No public workflows yet."
      @load-list="loadLibraryWorkflows"
      @handle-page-size="() => handleLibraryPageSize('workflows')"
      @select-workflow="openWorkflow"
    />
  </section>
</template>

<script setup lang="ts">
import { inject, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ResourceFilters from '../components/library/ResourceFilters.vue'
import ResourceList from '../components/library/ResourceList.vue'
import { hubStoreKey, useHubStore } from '../store/hubStore'
import type { WorkflowSummary } from '../types/hub'

const hubStore = inject(hubStoreKey) ?? useHubStore()
const router = useRouter()

const {
  librarySearchQuery,
  libraryTagFilter,
  libraryOwnerFilter,
  libraryPage,
  libraryPageSize,
  libraryWorkflows,
  libraryWorkflowTotal,
  libraryListLoading,
  libraryListError,
  loadLibraryWorkflows,
  applyLibraryFilters,
  resetLibraryFilters,
  handleLibraryPageSize
} = hubStore

function openWorkflow(flow: WorkflowSummary) {
  router.push(`/workflows/${encodeURIComponent(flow.id)}`)
}

function applyFilters() {
  applyLibraryFilters('workflows')
}

function resetFilters() {
  resetLibraryFilters('workflows')
}

onMounted(() => {
  loadLibraryWorkflows()
})
</script>
