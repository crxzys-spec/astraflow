<template>
  <div class="detail-body">
    <div class="detail-meta">
      <div>
        <span class="meta-label">Owner</span>
        <span>{{ workflow.ownerName || workflow.ownerId }}</span>
      </div>
      <div>
        <span class="meta-label">Visibility</span>
        <span>{{ workflow.visibility || 'public' }}</span>
      </div>
      <div>
        <span class="meta-label">Updated</span>
        <span>{{ formatDate(workflow.updatedAt) }}</span>
      </div>
    </div>
    <p class="detail-text">{{ workflow.summary || workflow.description || 'No summary.' }}</p>
    <div class="detail-tags">
      <el-tag v-for="tag in workflow.tags || []" :key="tag" size="small" type="info">
        {{ tag }}
      </el-tag>
    </div>
    <div v-if="previewSrc" class="detail-section">
      <div class="section-title">Preview</div>
      <div class="workflow-preview">
        <img :src="previewSrc" :alt="`${workflow.name} preview`" />
      </div>
    </div>
    <div class="detail-section">
      <div class="section-title">Versions</div>
      <div class="version-stack">
        <div
          v-for="ver in versions"
          :key="ver.id"
          class="version-row"
          :class="{ 'version-row--active': selectedVersion && selectedVersion.id === ver.id }"
          @click="selectVersion(ver)"
        >
          <div>
            <div class="version-name">{{ ver.version }}</div>
            <div class="version-meta">{{ formatDate(ver.publishedAt) }}</div>
          </div>
          <span class="version-chip">{{ ver.changelog || 'No changelog' }}</span>
        </div>
      </div>
    </div>
    <div class="detail-section">
      <div class="section-title">Dependencies</div>
      <div v-if="versionLoading" class="detail-empty">
        Loading dependencies...
      </div>
      <div v-else-if="versionError" class="detail-empty">
        {{ versionError }}
      </div>
      <div v-else-if="dependencies.length" class="dependency-list">
        <span
          v-for="dep in dependencies"
          :key="`${dep.name}@${dep.version}`"
          class="dependency-pill"
        >
          {{ dep.name }}@{{ dep.version }}
        </span>
      </div>
      <div v-else class="detail-empty">
        No dependencies declared.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PackageDependency, WorkflowDetail, WorkflowVersionDetail, WorkflowVersionSummary } from '../../types/hub'

const props = defineProps<{
  workflow: WorkflowDetail
  previewSrc: string
  versions: WorkflowVersionSummary[]
  selectedVersion: WorkflowVersionDetail | null
  versionLoading: boolean
  versionError: string
  dependencies: PackageDependency[]
}>()

const emit = defineEmits<{
  (e: 'select-version', ver: WorkflowVersionSummary): void
}>()

function selectVersion(ver: WorkflowVersionSummary) {
  emit('select-version', ver)
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
