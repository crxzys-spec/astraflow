<template>
  <div class="list-pane">
    <el-skeleton v-if="loading" animated :rows="6" />
    <template v-else>
      <div v-if="resourceType === 'packages'" class="card-grid">
        <el-card
          v-for="pkg in packages"
          :key="`${pkg.ownerId || pkg.ownerName || 'owner'}:${pkg.name}`"
          class="hub-card"
          shadow="never"
          @click="selectPackage(pkg)"
        >
          <div class="card-head">
            <div>
              <div class="card-title">{{ pkg.name }}</div>
              <div class="card-meta">
                v{{ pkg.latestVersion || 'n/a' }} by {{ pkg.ownerName || 'Unknown' }}
              </div>
            </div>
            <el-tag size="small" effect="dark" type="info">
              {{ pkg.visibility || 'public' }}
            </el-tag>
          </div>
          <p class="card-desc">{{ pkg.description || 'No description.' }}</p>
          <div class="card-tags">
            <el-tag v-for="tag in pkg.tags || []" :key="tag" size="small">
              {{ tag }}
            </el-tag>
          </div>
        </el-card>
      </div>

      <div v-else class="card-grid workflows">
        <el-card
          v-for="flow in workflows"
          :key="flow.id"
          class="hub-card"
          shadow="never"
          @click="selectWorkflow(flow)"
        >
          <div class="card-head">
            <div>
              <div class="card-title">{{ flow.name }}</div>
              <div class="card-meta">
                by {{ flow.ownerName || 'Unknown' }} on {{ formatDate(flow.updatedAt) }}
              </div>
            </div>
            <el-tag size="small" effect="dark" type="success">
              {{ flow.latestVersion || 'draft' }}
            </el-tag>
          </div>
          <p class="card-desc">{{ flow.summary || flow.description || 'No summary.' }}</p>
          <div class="card-tags">
            <el-tag v-for="tag in flow.tags || []" :key="tag" size="small" type="info">
              {{ tag }}
            </el-tag>
          </div>
        </el-card>
      </div>

      <el-empty
        v-if="!hasItems"
        :description="emptyText"
      />
    </template>

    <div class="pagination">
      <el-pagination
        v-model:current-page="pageModel"
        v-model:page-size="pageSizeModel"
        layout="sizes, prev, pager, next"
        :page-sizes="pageSizes"
        :total="total"
        @current-change="loadList"
        @size-change="handlePageSize"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PackageSummary, WorkflowSummary } from '../../types/hub'

const props = defineProps<{
  resourceType: 'packages' | 'workflows'
  packages: PackageSummary[]
  workflows: WorkflowSummary[]
  loading: boolean
  page: number
  pageSize: number
  total: number
  emptyText?: string
}>()

const emit = defineEmits<{
  (e: 'update:page', value: number): void
  (e: 'update:pageSize', value: number): void
  (e: 'load-list'): void
  (e: 'handle-page-size'): void
  (e: 'select-package', pkg: PackageSummary): void
  (e: 'select-workflow', flow: WorkflowSummary): void
}>()

const pageModel = computed({
  get: () => props.page,
  set: (value) => emit('update:page', value)
})

const pageSizeModel = computed({
  get: () => props.pageSize,
  set: (value) => emit('update:pageSize', value)
})

const pageSizes = [6, 12, 24, 48]

const hasItems = computed(() => {
  if (props.resourceType === 'packages') return props.packages.length > 0
  return props.workflows.length > 0
})

const emptyText = computed(() => props.emptyText || 'No records found')

function loadList() {
  emit('load-list')
}

function handlePageSize() {
  emit('handle-page-size')
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
