<template>
  <div class="detail-body">
    <div class="detail-meta">
      <div>
        <span class="meta-label">Owner</span>
        <span>{{ pkg.ownerName || pkg.ownerId }}</span>
      </div>
      <div>
        <span class="meta-label">Visibility</span>
        <span>{{ pkg.visibility || 'public' }}</span>
      </div>
      <div>
        <span class="meta-label">Updated</span>
        <span>{{ formatDate(pkg.updatedAt) }}</span>
      </div>
    </div>
    <p class="detail-text">{{ pkg.description || 'No description.' }}</p>
    <div class="detail-tags">
      <el-tag v-for="tag in pkg.tags || []" :key="tag" size="small">
        {{ tag }}
      </el-tag>
    </div>
    <div class="detail-section">
      <div class="section-title">Versions</div>
      <div class="version-list">
        <span v-for="ver in pkg.versions" :key="ver" class="version-pill">
          {{ ver }}
        </span>
      </div>
    </div>
    <div v-if="pkg.readme" class="detail-section">
      <div class="section-title">Readme</div>
      <pre class="detail-readme">{{ pkg.readme }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PackageDetail } from '../../types/hub'

defineProps<{
  pkg: PackageDetail
}>()

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
