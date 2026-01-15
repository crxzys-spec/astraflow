<template>
  <header class="hub-header" :class="{ 'hub-header--public': !hasToken }">
    <div class="header-left">
      <div class="brand">
        <span class="brand-mark">A</span>
        <div>
          <div class="brand-title">AstraFlow Hub</div>
          <div class="brand-subtitle">Secure discovery for packages and workflows.</div>
        </div>
      </div>
      <div class="header-search">
        <el-input
          v-model="searchQueryModel"
          class="hub-input hub-search"
          placeholder="Search packages/workflows"
          clearable
          @keyup.enter="search"
        />
        <el-button plain @click="search">Search</el-button>
      </div>
    </div>
    <div class="header-right">
      <nav class="header-nav">
        <RouterLink class="nav-link" to="/">Home</RouterLink>
        <RouterLink class="nav-link" to="/packages">Packages</RouterLink>
        <RouterLink class="nav-link" to="/workflows">Workflows</RouterLink>
        <RouterLink v-if="hasToken" class="nav-link" to="/console/packages">Console</RouterLink>
      </nav>
      <div class="header-actions">
        <el-dropdown v-if="hasToken" trigger="click" @command="handleCommand">
          <div class="account-trigger">
            <span class="account-avatar">{{ accountInitials }}</span>
            <div class="account-stack">
              <span class="account-name">{{ accountName }}</span>
              <span class="account-meta">Hub account</span>
            </div>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">Personal</el-dropdown-item>
              <el-dropdown-item command="orgs">Organizations</el-dropdown-item>
              <el-dropdown-item divided command="sign-out">Sign out</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button v-else plain @click="openAuth">Login / Register</el-button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AccountProfile, HubTab } from '../types/hub'

const props = defineProps<{
  hasToken: boolean
  searchQuery: string
  account?: AccountProfile | null
}>()

const emit = defineEmits<{
  (e: 'update:searchQuery', value: string): void
  (e: 'clear-auth'): void
  (e: 'open-auth'): void
  (e: 'search'): void
  (e: 'select-tab', value: HubTab): void
}>()

const searchQueryModel = computed({
  get: () => props.searchQuery,
  set: (value) => emit('update:searchQuery', value)
})

function clearAuth() {
  emit('clear-auth')
}

function openAuth() {
  emit('open-auth')
}

function search() {
  emit('search')
}

const accountName = computed(() => {
  if (!props.account) {
    return 'Account'
  }
  return props.account.displayName || props.account.username || 'Account'
})

const accountInitials = computed(() => {
  const name = accountName.value.trim()
  return name ? name[0].toUpperCase() : '?'
})

function handleCommand(command: 'profile' | 'orgs' | 'sign-out') {
  if (command === 'sign-out') {
    emit('clear-auth')
    return
  }
  emit('select-tab', command)
}
</script>
