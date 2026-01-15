<template>
  <ResourceList
    v-if="activeTab === 'packages' || activeTab === 'workflows'"
    :resourceType="activeTab === 'packages' ? 'packages' : 'workflows'"
    :packages="packages"
    :workflows="workflows"
    :loading="listLoading"
    v-model:page="pageModel"
    v-model:pageSize="pageSizeModel"
    :total="activeTotal"
    @load-list="loadList"
    @handle-page-size="handlePageSize"
    @select-package="selectPackage"
    @select-workflow="selectWorkflow"
  />

  <div v-else class="list-pane">
    <el-skeleton v-if="listLoading" animated :rows="6" />
    <template v-else>
      <div class="card-grid orgs">
        <el-card
          v-for="org in organizations"
          :key="org.id"
          class="hub-card"
          shadow="never"
          @click="selectOrganization(org)"
        >
          <div class="card-head">
            <div>
              <div class="card-title">{{ org.name }}</div>
              <div class="card-meta">Slug {{ org.slug }} - Owner {{ org.ownerId }}</div>
            </div>
            <el-tag size="small" effect="dark" type="warning">org</el-tag>
          </div>
          <p class="card-desc">
            Created {{ formatDate(org.createdAt) }} - Updated {{ formatDate(org.updatedAt) }}
          </p>
          <div class="card-actions">
            <el-button size="small" plain @click.stop="openOrgEdit(org)">Edit</el-button>
          </div>
        </el-card>
      </div>

      <el-empty
        v-if="!hasListData"
        description="No records found"
      />
    </template>

    <div class="pagination">
      <el-pagination
        v-model:current-page="pageModel"
        v-model:page-size="pageSizeModel"
        layout="sizes, prev, pager, next"
        :page-sizes="[6, 12, 24, 48]"
        :total="activeTotal"
        @current-change="loadList"
        @size-change="handlePageSize"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ResourceList from '../library/ResourceList.vue'
import type { HubTab, Organization, PackageSummary, WorkflowSummary } from '../../types/hub'

const props = defineProps<{
  activeTab: HubTab
  listLoading: boolean
  packages: PackageSummary[]
  workflows: WorkflowSummary[]
  organizations: Organization[]
  hasListData: boolean
  activeTotal: number
  page: number
  pageSize: number
}>()

const emit = defineEmits<{
  (e: 'update:page', value: number): void
  (e: 'update:pageSize', value: number): void
  (e: 'load-list'): void
  (e: 'handle-page-size'): void
  (e: 'select-package', pkg: PackageSummary): void
  (e: 'select-workflow', flow: WorkflowSummary): void
  (e: 'select-organization', org: Organization): void
  (e: 'open-org-edit', org: Organization): void
}>()

const pageModel = computed({
  get: () => props.page,
  set: (value) => emit('update:page', value)
})

const pageSizeModel = computed({
  get: () => props.pageSize,
  set: (value) => emit('update:pageSize', value)
})

function loadList() {
  emit('load-list')
}

function handlePageSize() {
  emit('handle-page-size')
}

function selectOrganization(org: Organization) {
  emit('select-organization', org)
}

function openOrgEdit(org: Organization) {
  emit('open-org-edit', org)
}

function selectPackage(pkg: PackageSummary) {
  emit('select-package', pkg)
}

function selectWorkflow(flow: WorkflowSummary) {
  emit('select-workflow', flow)
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
