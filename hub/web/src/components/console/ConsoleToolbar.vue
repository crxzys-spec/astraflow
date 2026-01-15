<template>
  <div class="workspace-header">
    <div class="console-title">
      <div class="detail-eyebrow">Console</div>
      <h3>{{ title }}</h3>
    </div>
    <div v-if="showOrgActions" class="console-actions">
      <el-button size="small" type="primary" @click="openOrgCreate">New organization</el-button>
    </div>
    <div v-if="showFilters" class="filters">
      <el-input v-model="searchQueryModel" placeholder="Search" clearable />
      <el-input v-model="tagFilterModel" placeholder="Tag" clearable />
      <el-input v-model="ownerFilterModel" placeholder="Owner" clearable />
      <el-button type="primary" @click="applyFilters">Search</el-button>
      <el-button plain @click="resetFilters">Reset</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { HubTab } from '../../types/hub'

const props = defineProps<{
  activeTab: HubTab
  searchQuery: string
  tagFilter: string
  ownerFilter: string
}>()

const emit = defineEmits<{
  (e: 'update:searchQuery', value: string): void
  (e: 'update:tagFilter', value: string): void
  (e: 'update:ownerFilter', value: string): void
  (e: 'apply-filters'): void
  (e: 'reset-filters'): void
  (e: 'open-org-create'): void
}>()

const searchQueryModel = computed({
  get: () => props.searchQuery,
  set: (value) => emit('update:searchQuery', value)
})

const tagFilterModel = computed({
  get: () => props.tagFilter,
  set: (value) => emit('update:tagFilter', value)
})

const ownerFilterModel = computed({
  get: () => props.ownerFilter,
  set: (value) => emit('update:ownerFilter', value)
})

const title = computed(() => {
  if (props.activeTab === 'workflows') return 'Workflows'
  if (props.activeTab === 'orgs') return 'Organizations'
  if (props.activeTab === 'profile') return 'Profile'
  if (props.activeTab === 'keys') return 'API keys'
  if (props.activeTab === 'devices') return 'Sessions'
  return 'Packages'
})

const showFilters = computed(() => {
  return props.activeTab === 'packages' || props.activeTab === 'workflows' || props.activeTab === 'orgs'
})

const showOrgActions = computed(() => props.activeTab === 'orgs')

function applyFilters() {
  emit('apply-filters')
}

function resetFilters() {
  emit('reset-filters')
}

function openOrgCreate() {
  emit('open-org-create')
}
</script>
