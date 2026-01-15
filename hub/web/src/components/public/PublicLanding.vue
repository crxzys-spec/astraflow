<template>
  <section class="public-hero">
    <div class="public-hero__content">
      <div class="public-eyebrow">AstraFlow Hub</div>
      <h1 class="public-title">Public hub for workflows and node packages.</h1>
      <p class="public-subtitle">
        <span v-if="hasToken">
          Browse public packages and workflows. Jump into the console for private assets.
        </span>
        <span v-else>
          Browse public packages and workflows. Sign in to view your private assets.
        </span>
      </p>
      <div class="public-actions">
        <el-button v-if="hasToken" type="primary" @click="openConsole">Open console</el-button>
        <el-button v-else type="primary" @click="openAuth">
          Sign in to view private assets
        </el-button>
      </div>
      <div class="public-search">
        <el-input
          v-model="searchQueryModel"
          class="hub-input public-search-input"
          placeholder="Search packages, workflows, tags"
          @keyup.enter="applyFilters"
        />
        <el-button type="primary" @click="applyFilters">Search</el-button>
        <el-button plain @click="resetFilters">Clear</el-button>
      </div>
      <div v-if="topTags.length" class="public-tags">
        <span class="tags-label">Tags</span>
        <button
          v-for="tag in topTags"
          :key="tag.name"
          class="tag-chip"
          :class="{ active: tagFilter === tag.name }"
          @click="selectTag(tag.name)"
        >
          {{ tag.name }}
        </button>
      </div>
    </div>
    <div class="public-hero__panel">
      <div class="public-stats">
        <div class="stat-card">
          <div class="stat-label">Packages indexed</div>
          <div class="stat-value">{{ packageTotalDisplay }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Workflows indexed</div>
          <div class="stat-value">{{ workflowTotalDisplay }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Access</div>
          <div class="stat-value">
            <span class="status-pill">Public catalog</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="public-content">
    <el-alert
      v-if="publicError"
      class="hub-alert"
      type="error"
      show-icon
      :closable="false"
      :title="publicError"
    />

    <div v-if="publicLoading" class="public-loading">
      <el-skeleton animated :rows="10" />
    </div>

    <div v-else class="public-layout">
      <div class="public-main">
        <div id="discover-packages" class="public-section">
          <div class="section-head">
            <div>
              <div class="section-eyebrow">Packages</div>
              <h2>Packages</h2>
            </div>
            <div class="section-meta">Public packages.</div>
          </div>
          <div class="public-grid">
            <el-card
              v-for="(pkg, index) in featuredPackages"
              :key="pkg.name"
              class="public-card"
              shadow="never"
              :style="{ '--delay': `${index * 70}ms` }"
              @click="openPackage(pkg)"
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
            <div v-if="!featuredPackages.length" class="public-empty">
              No public packages yet.
            </div>
          </div>
        </div>

        <div id="discover-workflows" class="public-section">
          <div class="section-head">
            <div>
              <div class="section-eyebrow">Workflows</div>
              <h2>Workflows</h2>
            </div>
            <div class="section-meta">Public workflows.</div>
          </div>
          <div class="public-grid">
            <el-card
              v-for="(flow, index) in featuredWorkflows"
              :key="flow.id"
              class="public-card"
              shadow="never"
              :style="{ '--delay': `${index * 70}ms` }"
              @click="openWorkflow(flow)"
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
            <div v-if="!featuredWorkflows.length" class="public-empty">
              No public workflows yet.
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PackageSummary, WorkflowSummary } from '../../types/hub'

interface TagStat {
  name: string
  count: number
}

const props = defineProps<{
  packageTotalDisplay: string
  workflowTotalDisplay: string
  searchQuery: string
  tagFilter: string
  topTags: TagStat[]
  featuredPackages: PackageSummary[]
  featuredWorkflows: WorkflowSummary[]
  publicLoading: boolean
  publicError: string
  hasToken: boolean
}>()

const emit = defineEmits<{
  (e: 'update:searchQuery', value: string): void
  (e: 'open-auth'): void
  (e: 'open-console'): void
  (e: 'apply-filters'): void
  (e: 'reset-filters'): void
  (e: 'select-tag', tag: string): void
  (e: 'open-package', pkg: PackageSummary): void
  (e: 'open-workflow', flow: WorkflowSummary): void
}>()

const searchQueryModel = computed({
  get: () => props.searchQuery,
  set: (value) => emit('update:searchQuery', value)
})

function applyFilters() {
  emit('apply-filters')
}

function resetFilters() {
  emit('reset-filters')
}

function openAuth() {
  emit('open-auth')
}

function openConsole() {
  emit('open-console')
}

function selectTag(tag: string) {
  emit('select-tag', tag)
}

function openPackage(pkg: PackageSummary) {
  emit('open-package', pkg)
}

function openWorkflow(flow: WorkflowSummary) {
  emit('open-workflow', flow)
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
