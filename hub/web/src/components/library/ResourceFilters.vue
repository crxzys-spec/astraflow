<template>
  <div class="resource-header">
    <div class="resource-title">
      <div class="detail-eyebrow">Library</div>
      <h3>{{ title }}</h3>
      <p v-if="subtitle" class="resource-subtitle">{{ subtitle }}</p>
    </div>
    <div class="filters">
      <el-input v-model="searchQueryModel" placeholder="Search" clearable />
      <el-input v-if="showTag" v-model="tagFilterModel" placeholder="Tag" clearable />
      <el-input v-if="showOwner" v-model="ownerFilterModel" placeholder="Owner" clearable />
      <el-button type="primary" @click="applyFilters">Search</el-button>
      <el-button plain @click="resetFilters">Reset</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  subtitle?: string
  searchQuery: string
  tagFilter: string
  ownerFilter: string
  showTag?: boolean
  showOwner?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:searchQuery', value: string): void
  (e: 'update:tagFilter', value: string): void
  (e: 'update:ownerFilter', value: string): void
  (e: 'apply-filters'): void
  (e: 'reset-filters'): void
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

const showTag = computed(() => props.showTag !== false)
const showOwner = computed(() => props.showOwner !== false)

function applyFilters() {
  emit('apply-filters')
}

function resetFilters() {
  emit('reset-filters')
}
</script>
