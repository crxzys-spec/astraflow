<template>
  <div class="hub-app">
    <div class="ambient-grid"></div>
    <HubHeader
      :hasToken="hasToken"
      :account="accountProfile"
      v-model:searchQuery="headerSearchQuery"
      @clear-auth="handleClearAuth"
      @open-auth="openAuthDialog"
      @search="handleHeaderSearch"
      @select-tab="handleSelectTab"
    />

    <main class="hub-main">
      <RouterView />
    </main>

    <el-dialog
      v-model="authDialogOpen"
      width="460px"
      class="auth-dialog"
      modal-class="auth-overlay"
      :show-close="false"
    >
      <template #header>
        <div class="auth-header">
          <div>
            <div class="auth-eyebrow">Hub access</div>
            <h3>{{ authMode === 'login' ? 'Login' : 'Create account' }}</h3>
          </div>
          <el-button text @click="authDialogOpen = false">Close</el-button>
        </div>
      </template>

      <el-tabs v-model="authMode" class="auth-tabs">
        <el-tab-pane label="Login" name="login">
          <el-form label-position="top" class="auth-form">
            <el-form-item label="Username">
              <el-input v-model="authForm.username" autocomplete="username" />
            </el-form-item>
            <el-form-item label="Password">
              <el-input v-model="authForm.password" type="password" show-password autocomplete="current-password" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="Register" name="register">
          <el-form label-position="top" class="auth-form">
            <el-form-item label="Username">
              <el-input v-model="authForm.username" autocomplete="username" />
            </el-form-item>
            <el-form-item label="Password">
              <el-input v-model="authForm.password" type="password" show-password autocomplete="new-password" />
            </el-form-item>
            <el-form-item label="Display name">
              <el-input v-model="authForm.displayName" />
            </el-form-item>
            <el-form-item label="Email">
              <el-input v-model="authForm.email" type="email" autocomplete="email" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <el-alert
        v-if="authError"
        type="error"
        show-icon
        :closable="false"
        :title="authError"
      />

      <template #footer>
        <div class="auth-footer">
          <el-button plain @click="resetAuthForm">Reset</el-button>
          <el-button type="primary" :loading="authLoading" @click="submitAuth">
            {{ authMode === 'login' ? 'Login' : 'Register' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="orgEditOpen"
      width="420px"
      class="edit-dialog"
      :show-close="false"
    >
      <template #header>
        <div class="auth-header">
          <div>
            <div class="auth-eyebrow">Organization</div>
            <h3>{{ orgEditTarget ? 'Edit organization' : 'Create organization' }}</h3>
          </div>
          <el-button text @click="orgEditOpen = false">Close</el-button>
        </div>
      </template>

      <el-form label-position="top" class="auth-form">
        <el-form-item label="Name">
          <el-input v-model="orgEditForm.name" />
        </el-form-item>
        <el-form-item label="Slug">
          <el-input v-model="orgEditForm.slug" />
        </el-form-item>
      </el-form>

      <el-alert
        v-if="orgEditError"
        type="error"
        show-icon
        :closable="false"
        :title="orgEditError"
      />

      <template #footer>
        <div class="auth-footer">
          <el-button plain @click="orgEditOpen = false">Cancel</el-button>
          <el-button type="primary" :loading="orgEditLoading" @click="submitOrgEdit">
            {{ orgEditTarget ? 'Save' : 'Create' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="orgInviteOpen"
      width="460px"
      class="edit-dialog"
      :show-close="false"
    >
      <template #header>
        <div class="auth-header">
          <div>
            <div class="auth-eyebrow">Organization</div>
            <h3>Invite member</h3>
          </div>
          <el-button text @click="orgInviteOpen = false">Close</el-button>
        </div>
      </template>

      <el-form label-position="top" class="auth-form">
        <el-form-item label="User ID or email">
          <el-input v-model="orgInviteForm.userId" placeholder="username or email" />
        </el-form-item>
        <el-form-item label="Role">
          <el-select v-model="orgInviteForm.role" placeholder="Select role">
            <el-option label="Member" value="member" />
            <el-option label="Admin" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="Expires at (optional)">
          <el-input v-model="orgInviteForm.expiresAt" placeholder="2026-12-31T00:00:00Z" />
        </el-form-item>
      </el-form>

      <el-alert
        v-if="orgInviteError"
        type="error"
        show-icon
        :closable="false"
        :title="orgInviteError"
      />

      <template #footer>
        <div class="auth-footer">
          <el-button plain @click="orgInviteOpen = false">Cancel</el-button>
          <el-button type="primary" :loading="orgInviteLoading" @click="submitOrgInvite">
            Send invite
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import HubHeader from './layouts/HubHeader.vue'
import { hubStoreKey, useHubStore } from './store/hubStore'

const hubStore = useHubStore()
const route = useRoute()
const router = useRouter()
provide(hubStoreKey, hubStore)

const {
  hasToken,
  accountProfile,
  searchQuery,
  librarySearchQuery,
  clearAuth,
  openAuthDialog,
  applyConsoleFilters,
  applyLibraryFilters,
  authDialogOpen,
  authMode,
  authError,
  authForm,
  authLoading,
  resetAuthForm,
  submitAuth,
  orgEditOpen,
  orgEditForm,
  orgEditError,
  orgEditLoading,
  orgEditTarget,
  submitOrgEdit,
  orgInviteOpen,
  orgInviteForm,
  orgInviteError,
  orgInviteLoading,
  createOrgInvite,
  selectedOrg
} = hubStore

const isConsoleRoute = computed(() => route.path.startsWith('/console'))
const headerSearchQuery = computed({
  get: () => (isConsoleRoute.value ? searchQuery.value : librarySearchQuery.value),
  set: (value) => {
    if (isConsoleRoute.value) {
      searchQuery.value = value
    } else {
      librarySearchQuery.value = value
    }
  }
})

function handleHeaderSearch() {
  if (isConsoleRoute.value) {
    applyConsoleFilters()
    return
  }
  if (route.path.startsWith('/workflows/')) {
    router.push('/workflows')
    applyLibraryFilters('workflows')
    return
  }
  if (route.path.startsWith('/packages/')) {
    router.push('/packages')
    applyLibraryFilters('packages')
    return
  }
  if (route.path.startsWith('/workflows')) {
    applyLibraryFilters('workflows')
    return
  }
  if (route.path.startsWith('/packages')) {
    applyLibraryFilters('packages')
    return
  }
  applyLibraryFilters('snapshot')
}

async function submitOrgInvite() {
  if (!selectedOrg.value) {
    orgInviteError.value = 'Select an organization to invite members.'
    return
  }
  await createOrgInvite(selectedOrg.value.id)
}

function handleClearAuth() {
  clearAuth()
  if (router.currentRoute.value.path !== '/') {
    router.push('/')
  }
}

function handleSelectTab(tab: 'packages' | 'workflows' | 'orgs' | 'profile' | 'keys' | 'devices') {
  if (!hasToken.value) {
    openAuthDialog()
    return
  }
  hubStore.activeTab.value = tab
  const target = `/console/${tab}`
  if (router.currentRoute.value.path !== target) {
    router.push(target)
  }
}
</script>

<style>
.hub-app {
  position: relative;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
}

.hub-app::before,
.hub-app::after {
  content: '';
  position: fixed;
  inset: 0;
  background: radial-gradient(circle at top, rgba(79, 209, 197, 0.22), transparent 60%),
    radial-gradient(circle at 40% 20%, rgba(255, 184, 77, 0.18), transparent 55%);
  pointer-events: none;
  z-index: 0;
}

.hub-app::after {
  background: radial-gradient(circle at 20% 30%, rgba(85, 120, 255, 0.18), transparent 60%),
    radial-gradient(circle at 80% 70%, rgba(79, 209, 197, 0.2), transparent 60%);
}

.ambient-grid {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 120px 120px;
  mask-image: radial-gradient(circle at top, black 30%, transparent 70%);
  opacity: 0.5;
  z-index: 0;
}

.hub-header {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 48px;
  background: rgba(7, 11, 20, 0.78);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(120, 160, 220, 0.15);
}

.hub-header--public {
  background: rgba(6, 10, 18, 0.6);
  border-bottom: 1px solid rgba(120, 160, 220, 0.1);
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.header-search {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-left: auto;
  flex-wrap: wrap;
}

.nav-link {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  letter-spacing: 0.5px;
  color: var(--hub-muted);
  border: 1px solid transparent;
  transition: color 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.nav-link:hover {
  color: var(--hub-text);
  border-color: rgba(79, 209, 197, 0.4);
  background: rgba(79, 209, 197, 0.1);
}

.brand {
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-weight: 700;
  background: linear-gradient(130deg, #4fd1c5, #3182ce);
  color: #051016;
  box-shadow: 0 12px 28px rgba(79, 209, 197, 0.35);
}

.brand-title {
  font-size: 18px;
  font-weight: 600;
}

.brand-subtitle {
  font-size: 12px;
  color: var(--hub-muted);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hub-input {
  width: 220px;
}

.hub-search {
  width: 280px;
}

.hub-main {
  position: relative;
  z-index: 1;
  padding: 32px 48px 80px;
  display: flex;
  flex-direction: column;
  gap: 32px;
  flex: 1 1 auto;
  min-height: 0;
}

.public-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 360px);
  gap: 28px;
  padding: 32px;
  border-radius: 28px;
  background: linear-gradient(120deg, rgba(15, 26, 44, 0.92), rgba(7, 12, 22, 0.82));
  border: 1px solid rgba(120, 160, 220, 0.2);
  overflow: hidden;
  animation: hero-fade 0.6s ease forwards;
}

.public-hero::before {
  content: '';
  position: absolute;
  inset: -40% -10% auto -10%;
  height: 90%;
  background: radial-gradient(circle at 20% 20%, rgba(79, 209, 197, 0.22), transparent 60%),
    radial-gradient(circle at 60% 10%, rgba(255, 184, 77, 0.18), transparent 55%);
  opacity: 0.9;
  pointer-events: none;
}

.public-hero__content,
.public-hero__panel {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.public-eyebrow {
  text-transform: uppercase;
  letter-spacing: 3px;
  font-size: 11px;
  color: var(--hub-accent);
}

.public-title {
  margin: 0;
  font-size: clamp(32px, 4vw, 52px);
  line-height: 1.05;
}

.public-subtitle {
  margin: 0;
  color: var(--hub-muted);
  max-width: 560px;
}

.public-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.public-search {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.public-search-input {
  flex: 1;
  min-width: 220px;
}

.public-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.tags-label {
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 11px;
  color: var(--hub-muted);
}

.tag-chip {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(79, 209, 197, 0.35);
  background: rgba(79, 209, 197, 0.12);
  color: #b8f3ea;
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease, background 0.2s ease;
}

.tag-chip.active,
.tag-chip:hover {
  border-color: rgba(255, 184, 77, 0.7);
  color: #ffd79b;
  background: rgba(255, 184, 77, 0.18);
}

.public-stats {
  display: grid;
  gap: 12px;
}

.stat-card {
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(120, 160, 220, 0.18);
  background: rgba(10, 16, 28, 0.75);
  box-shadow: inset 0 0 20px rgba(79, 209, 197, 0.05);
}

.stat-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--hub-muted);
  margin-bottom: 6px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
}



.public-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.public-loading {
  padding: 16px;
  border-radius: 20px;
  background: rgba(10, 16, 28, 0.6);
  border: 1px solid rgba(120, 160, 220, 0.16);
}

.public-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 24px;
}

.public-main {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.public-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.section-eyebrow {
  text-transform: uppercase;
  letter-spacing: 2px;
  font-size: 11px;
  color: var(--hub-accent);
}

.section-meta {
  font-size: 12px;
  color: var(--hub-muted);
}

.public-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.public-card {
  background: rgba(12, 20, 34, 0.88);
  border: 1px solid rgba(120, 160, 220, 0.2);
  border-radius: 18px;
  color: inherit;
  cursor: pointer;
  box-shadow: inset 0 0 20px rgba(79, 209, 197, 0.04);
  opacity: 0;
  transform: translateY(16px);
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  animation: card-rise 0.6s ease forwards;
  animation-delay: var(--delay, 0ms);
}

.public-card:hover {
  transform: translateY(-3px);
  border-color: rgba(79, 209, 197, 0.35);
  box-shadow: 0 14px 26px rgba(4, 8, 18, 0.35);
}

.public-card .el-card__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.public-empty {
  font-size: 12px;
  color: var(--hub-muted);
  padding: 12px;
}



.public-footer {
  padding: 28px;
  border-radius: 24px;
  border: 1px solid rgba(120, 160, 220, 0.2);
  background: rgba(10, 16, 28, 0.7);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.status-panel {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 24px 26px;
  border-radius: 26px;
  border: 1px solid rgba(120, 160, 220, 0.18);
  background: linear-gradient(120deg, rgba(12, 20, 34, 0.92), rgba(7, 12, 22, 0.75));
  box-shadow: 0 24px 48px rgba(4, 8, 18, 0.55), inset 0 0 24px rgba(79, 209, 197, 0.05);
  overflow: hidden;
}

.status-panel::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  height: 2px;
  width: 100%;
  background: linear-gradient(90deg, rgba(79, 209, 197, 0.7), rgba(58, 169, 255, 0));
  opacity: 0.7;
}

.status-eyebrow {
  text-transform: uppercase;
  letter-spacing: 2px;
  font-size: 11px;
  color: var(--hub-accent);
  margin-bottom: 12px;
}

.status-panel h1 {
  margin: 0 0 12px;
  font-size: clamp(28px, 3vw, 44px);
}

.status-subtitle {
  color: var(--hub-muted);
  max-width: 520px;
}

.status-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 160px));
  gap: 16px;
}

.status-card {
  padding: 16px;
  border-radius: 16px;
  background: rgba(10, 16, 28, 0.7);
  border: 1px solid rgba(120, 160, 220, 0.16);
  box-shadow: inset 0 0 18px rgba(79, 209, 197, 0.05);
}

.status-label {
  font-size: 12px;
  color: var(--hub-muted);
  margin-bottom: 6px;
}

.status-value {
  font-size: 18px;
  font-weight: 600;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 184, 77, 0.2);
  color: #ffd494;
  font-size: 12px;
}

.status-pill.ready {
  background: rgba(79, 209, 197, 0.2);
  color: #8ff5ea;
}

.workspace {
  background: linear-gradient(180deg, rgba(10, 16, 28, 0.78), rgba(7, 12, 22, 0.9));
  border: 1px solid rgba(120, 160, 220, 0.18);
  border-radius: 24px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex: 1 1 auto;
  min-height: 0;
  box-shadow: 0 18px 40px rgba(4, 8, 18, 0.45), inset 0 0 30px rgba(79, 209, 197, 0.04);
}

.console-shell {
  display: flex;
  align-items: stretch;
  gap: 24px;
  flex: 1 1 auto;
  min-height: 0;
}

.console-nav {
  background: linear-gradient(180deg, rgba(10, 16, 28, 0.92), rgba(7, 12, 22, 0.85));
  border: 1px solid rgba(120, 160, 220, 0.18);
  border-radius: 20px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-self: flex-start;
  flex: 0 0 220px;
  backdrop-filter: blur(14px);
  box-shadow: 0 14px 32px rgba(4, 8, 16, 0.45), inset 0 0 18px rgba(79, 209, 197, 0.04);
}

.console-nav-title {
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--hub-muted);
}

.console-nav-title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(79, 209, 197, 0.55), rgba(58, 169, 255, 0));
}

.console-nav-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.console-nav-item {
  position: relative;
  width: 100%;
  text-align: left;
  padding: 10px 14px 10px 18px;
  border-radius: 12px;
  border: 1px solid rgba(120, 160, 220, 0.12);
  background: rgba(10, 16, 28, 0.5);
  color: var(--hub-muted);
  font-size: 13px;
  letter-spacing: 0.4px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.console-nav-item::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 55%;
  border-radius: 999px;
  background: transparent;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.console-nav-item:hover {
  color: var(--hub-text);
  border-color: rgba(79, 209, 197, 0.28);
  background: rgba(79, 209, 197, 0.08);
  transform: translateX(2px);
}

.console-nav-item--active {
  color: var(--hub-text);
  border-color: rgba(79, 209, 197, 0.55);
  background: linear-gradient(130deg, rgba(79, 209, 197, 0.18), rgba(58, 169, 255, 0.12));
  box-shadow: inset 0 0 0 1px rgba(79, 209, 197, 0.18);
}

.console-nav-item--active::before {
  background: linear-gradient(180deg, rgba(79, 209, 197, 0.9), rgba(58, 169, 255, 0.8));
  box-shadow: 0 0 12px rgba(79, 209, 197, 0.6);
}

.console-title {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.console-title h3 {
  margin: 0;
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(120, 160, 220, 0.14);
}

.console-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.library-shell {
  gap: 20px;
}

.resource-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(120, 160, 220, 0.14);
}

.resource-title {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.resource-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--hub-muted);
  max-width: 520px;
}

.filters {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.hub-alert {
  margin-bottom: 4px;
}

.workspace-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 360px);
  gap: 24px;
  flex: 1 1 auto;
  min-height: 0;
}

.list-pane {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1 1 auto;
  min-height: 0;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.hub-card {
  background: linear-gradient(180deg, rgba(12, 20, 34, 0.78), rgba(9, 15, 26, 0.6));
  border: 1px solid rgba(120, 160, 220, 0.1);
  border-radius: 18px;
  color: inherit;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 10px 22px rgba(4, 8, 16, 0.35);
}

.hub-card:hover {
  transform: translateY(-3px);
  border-color: rgba(79, 209, 197, 0.25);
  box-shadow: 0 16px 30px rgba(4, 8, 16, 0.45);
}

.hub-card .el-card__body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.card-meta {
  font-size: 12px;
  color: var(--hub-muted);
}

.card-desc {
  margin: 0;
  color: var(--hub-muted);
  font-size: 13px;
  min-height: 42px;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid rgba(120, 160, 220, 0.12);
}

.detail-pane {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.detail-card {
  background: linear-gradient(180deg, rgba(12, 20, 34, 0.82), rgba(9, 15, 26, 0.65));
  border: 1px solid rgba(120, 160, 220, 0.14);
  border-radius: 20px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1 1 auto;
  min-height: 0;
  box-shadow: 0 16px 30px rgba(4, 8, 16, 0.4);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(120, 160, 220, 0.12);
}

.detail-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
}

.detail-eyebrow {
  text-transform: uppercase;
  letter-spacing: 2px;
  font-size: 11px;
  color: var(--hub-accent-2);
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-meta {
  display: grid;
  gap: 8px;
  font-size: 12px;
  color: var(--hub-muted);
}

.detail-meta span {
  color: var(--hub-text);
}

.meta-label {
  display: block;
  font-size: 11px;
  color: var(--hub-muted);
}

.detail-text {
  margin: 0;
  color: var(--hub-muted);
  font-size: 13px;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--hub-muted);
}

.version-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.version-pill {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(79, 209, 197, 0.15);
  font-size: 12px;
}

.version-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.version-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(10, 16, 28, 0.7);
  border: 1px solid rgba(120, 160, 220, 0.2);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.version-row--active {
  border-color: rgba(79, 209, 197, 0.6);
  box-shadow: inset 0 0 0 1px rgba(79, 209, 197, 0.3);
}

.version-name {
  font-weight: 600;
}

.version-meta {
  font-size: 11px;
  color: var(--hub-muted);
}

.version-chip {
  font-size: 11px;
  color: var(--hub-muted);
  align-self: center;
}

.detail-readme {
  margin: 0;
  padding: 12px;
  border-radius: 12px;
  background: rgba(7, 12, 22, 0.7);
  border: 1px solid rgba(120, 160, 220, 0.15);
  font-size: 12px;
  color: var(--hub-muted);
  white-space: pre-wrap;
}

.workflow-preview {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(120, 160, 220, 0.2);
  background: rgba(7, 12, 22, 0.7);
}

.workflow-preview img {
  display: block;
  width: 100%;
  height: auto;
}

.dependency-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.dependency-pill {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(49, 130, 206, 0.18);
  font-size: 12px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-count {
  font-size: 11px;
  color: var(--hub-muted);
}

.detail-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(10, 16, 28, 0.7);
  border: 1px solid rgba(120, 160, 220, 0.2);
}

.detail-row__main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.detail-row__title {
  font-weight: 600;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.detail-row__meta {
  font-size: 11px;
  color: var(--hub-muted);
}

.detail-row__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.detail-chip {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  border: 1px solid rgba(79, 209, 197, 0.35);
  background: rgba(79, 209, 197, 0.12);
  color: var(--hub-accent);
}

.detail-chip--pending {
  border-color: rgba(255, 184, 77, 0.4);
  background: rgba(255, 184, 77, 0.15);
  color: var(--hub-accent-2);
}

.detail-chip--accepted {
  border-color: rgba(79, 209, 197, 0.4);
  background: rgba(79, 209, 197, 0.12);
  color: var(--hub-accent);
}

.detail-chip--declined,
.detail-chip--revoked,
.detail-chip--expired {
  border-color: rgba(120, 160, 220, 0.25);
  background: rgba(120, 160, 220, 0.12);
  color: var(--hub-muted);
}

.detail-chip--role {
  border-color: rgba(120, 160, 220, 0.3);
  background: rgba(120, 160, 220, 0.1);
  color: var(--hub-text);
}

.permission-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(7, 12, 22, 0.7);
  border: 1px solid rgba(120, 160, 220, 0.16);
}

.permission-form__title {
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--hub-muted);
}

.permission-form__grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  align-items: center;
}

.permission-form__grid .el-button {
  justify-self: start;
}

.detail-empty {
  color: var(--hub-muted);
  font-size: 13px;
}

.account-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 24px;
  align-items: stretch;
  flex: 1 1 auto;
  min-height: 0;
}

.account-layout--single {
  grid-template-columns: minmax(0, 1fr);
}

.account-layout--keys {
  grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
}

.account-layout--sessions {
  grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
}

.account-card {
  min-height: 0;
}

.account-panels {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.account-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.account-meta {
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.account-form {
  display: grid;
  gap: 16px;
}

.account-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 8px;
}

.session-list {
  max-height: min(360px, 55vh);
}

.account-keys-list .detail-body,
.account-sessions-list .detail-body {
  flex: 1 1 auto;
  min-height: 0;
}

.account-sessions-list .session-list {
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
}

.session-row {
  position: relative;
  width: 100%;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, background 0.2s ease;
  padding: 14px 16px;
  color: var(--hub-text);
  background: linear-gradient(
    120deg,
    rgba(79, 209, 197, 0.08),
    rgba(9, 16, 28, 0.9) 36%,
    rgba(7, 12, 22, 0.6)
  );
  border: 1px solid rgba(120, 160, 220, 0.16);
  box-shadow: inset 4px 0 0 rgba(79, 209, 197, 0.12);
}

.session-row .token-info {
  flex: 1 1 auto;
  min-width: 0;
  gap: 12px;
}

.session-row:hover {
  border-color: rgba(79, 209, 197, 0.25);
  transform: translateX(2px);
  background: linear-gradient(130deg, rgba(12, 24, 36, 0.94), rgba(9, 15, 26, 0.7));
  box-shadow: inset 4px 0 0 rgba(79, 209, 197, 0.38);
}

.session-row--active {
  border-color: rgba(79, 209, 197, 0.55);
  background: linear-gradient(130deg, rgba(79, 209, 197, 0.22), rgba(58, 169, 255, 0.08));
  box-shadow: 0 10px 24px rgba(4, 8, 18, 0.35), inset 4px 0 0 rgba(79, 209, 197, 0.9);
}

.session-row__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.session-row__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--hub-text);
}

.session-row__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
  font-size: 12px;
  color: rgba(176, 194, 224, 0.82);
  line-height: 1.4;
}

.session-row__meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.session-row__meta-label {
  font-size: 10px;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: rgba(148, 168, 200, 0.7);
}

.session-row__meta-value {
  font-size: 12px;
  color: rgba(188, 206, 236, 0.95);
}

.session-row__id {
  align-self: flex-start;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(120, 160, 220, 0.2);
  background: rgba(10, 16, 28, 0.65);
  font-size: 10px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: rgba(176, 194, 224, 0.78);
}

.session-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(120, 160, 220, 0.2);
  background: rgba(10, 16, 28, 0.7);
  font-size: 11px;
  letter-spacing: 0.6px;
  color: var(--hub-muted);
  text-transform: uppercase;
}

.session-chip--current {
  color: #8ff5ea;
  border-color: rgba(79, 209, 197, 0.5);
  background: linear-gradient(135deg, rgba(79, 209, 197, 0.22), rgba(58, 169, 255, 0.12));
  box-shadow: inset 0 0 0 1px rgba(79, 209, 197, 0.2);
}

.session-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(120, 160, 220, 0.12);
}

.session-detail-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-detail-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-detail-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--hub-text);
}

.session-detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 320px);
  gap: 18px;
  align-items: start;
}

.session-detail-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.session-detail-aside {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.session-section {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(120, 160, 220, 0.16);
  background: rgba(8, 14, 24, 0.55);
  box-shadow: inset 0 0 10px rgba(79, 209, 197, 0.04);
}

.session-section .section-title {
  margin-bottom: 8px;
}

.session-kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.session-kpi {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(120, 160, 220, 0.18);
  background: linear-gradient(180deg, rgba(9, 16, 28, 0.88), rgba(7, 12, 22, 0.75));
  box-shadow: inset 0 0 14px rgba(79, 209, 197, 0.05);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.session-kpi__label {
  font-size: 10px;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: var(--hub-muted);
}

.session-kpi__value {
  font-size: 13px;
  font-weight: 600;
  color: var(--hub-text);
}

.session-kpi__value--muted {
  color: var(--hub-muted);
}

.session-meta-grid {
  border-top: 1px dashed rgba(120, 160, 220, 0.18);
  padding-top: 12px;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.session-agent {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(120, 160, 220, 0.18);
  background: linear-gradient(180deg, rgba(9, 16, 28, 0.85), rgba(7, 12, 22, 0.7));
  box-shadow: inset 0 0 12px rgba(79, 209, 197, 0.05);
}

.session-agent-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--hub-text);
}

.session-agent-item .meta-label {
  margin-bottom: 0;
}

.account-sessions-list,
.account-sessions-detail {
  position: relative;
  overflow: hidden;
}

.account-sessions-list::after,
.account-sessions-detail::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(79, 209, 197, 0.08) 1px, transparent 1px);
  background-size: 18px 18px;
  opacity: 0.25;
  pointer-events: none;
}

.account-sessions-list > *,
.account-sessions-detail > * {
  position: relative;
  z-index: 1;
}

.session-detail {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(120, 160, 220, 0.16);
  background: rgba(8, 14, 24, 0.55);
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 100%;
}

.session-meta {
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.session-meta--wide {
  grid-column: 1 / -1;
  word-break: break-word;
}

.session-actions {
  margin-top: auto;
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(79, 209, 197, 0.35);
  background: linear-gradient(135deg, rgba(10, 18, 30, 0.92), rgba(7, 12, 22, 0.88));
  box-shadow: 0 -12px 24px rgba(4, 8, 18, 0.35), inset 0 0 16px rgba(79, 209, 197, 0.08);
}

.session-actions .section-title {
  margin: 0;
}

.session-actions .el-button {
  min-width: 120px;
  justify-content: center;
  border: none;
  color: #07121c;
  font-weight: 600;
  background: linear-gradient(135deg, rgba(79, 209, 197, 0.95), rgba(58, 169, 255, 0.9));
  box-shadow: 0 8px 20px rgba(4, 8, 18, 0.35);
}

.session-actions .el-button:hover {
  filter: brightness(1.05);
}

.session-actions .el-button.is-disabled {
  color: rgba(176, 194, 224, 0.7);
  background: rgba(10, 16, 28, 0.7);
  border: 1px solid rgba(120, 160, 220, 0.2);
  box-shadow: none;
}

.token-form {
  margin-top: 8px;
}

.key-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.key-callout {
  border-radius: 14px;
  padding: 12px 14px;
  border: 1px solid rgba(79, 209, 197, 0.25);
  background: linear-gradient(135deg, rgba(79, 209, 197, 0.14), rgba(58, 169, 255, 0.08));
  box-shadow: inset 0 0 0 1px rgba(79, 209, 197, 0.08);
}

.key-callout-title {
  text-transform: uppercase;
  letter-spacing: 2px;
  font-size: 11px;
  color: var(--hub-accent-2);
  margin-bottom: 6px;
}

.key-callout-text {
  font-size: 13px;
  line-height: 1.5;
  color: var(--hub-text);
}

.key-form-panel {
  padding: 14px;
  border-radius: 16px;
  border: 1px solid rgba(120, 160, 220, 0.16);
  background: rgba(8, 14, 24, 0.55);
}

.key-form-section + .key-form-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(120, 160, 220, 0.2);
}

.key-form-title {
  text-transform: uppercase;
  letter-spacing: 1.6px;
  font-size: 11px;
  color: var(--hub-muted);
  margin-bottom: 6px;
}

.key-scope-group .el-checkbox {
  margin-right: 12px;
}

.key-form-actions {
  justify-content: space-between;
}

.key-result-panel {
  border-color: rgba(79, 209, 197, 0.35);
  background: linear-gradient(150deg, rgba(9, 18, 28, 0.92), rgba(7, 12, 22, 0.88));
  box-shadow: 0 18px 40px rgba(4, 8, 18, 0.35);
}

.key-result-panel .token-secret {
  background: rgba(8, 14, 24, 0.9);
}

.token-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.token-result {
  margin-top: 16px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(120, 160, 220, 0.2);
  background: rgba(7, 12, 22, 0.75);
}

.token-result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.token-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.token-result-meta {
  font-size: 12px;
  color: var(--hub-muted);
  display: flex;
  align-items: center;
  gap: 8px;
}

.token-secret {
  margin: 10px 0 12px;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid rgba(120, 160, 220, 0.2);
  background: rgba(10, 16, 28, 0.8);
  font-size: 12px;
  color: var(--hub-text);
  word-break: break-all;
}

.token-result-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.key-inline-secret {
  padding: 12px;
  border-radius: 14px;
  background: rgba(8, 14, 24, 0.6);
}

.key-inline-secret .token-secret {
  margin: 8px 0 0;
}

.token-copy {
  font-size: 11px;
  color: var(--hub-muted);
}

.token-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.token-stack--scroll {
  max-height: min(360px, 55vh);
  overflow-y: auto;
  padding-right: 6px;
  scrollbar-width: thin;
  scrollbar-color: rgba(79, 209, 197, 0.55) rgba(10, 16, 28, 0.4);
}

.token-stack--scroll::-webkit-scrollbar {
  width: 8px;
}

.token-stack--scroll::-webkit-scrollbar-track {
  background: rgba(10, 16, 28, 0.35);
  border-radius: 999px;
}

.token-stack--scroll::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, rgba(79, 209, 197, 0.75), rgba(58, 169, 255, 0.6));
  border-radius: 999px;
  border: 2px solid rgba(10, 16, 28, 0.4);
}

.token-stack--scroll::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, rgba(99, 235, 224, 0.9), rgba(82, 192, 255, 0.8));
}

.token-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(8, 14, 24, 0.5);
  border: 1px solid rgba(120, 160, 220, 0.12);
}

.key-row {
  width: 100%;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, background 0.2s ease;
}

.key-row:hover {
  border-color: rgba(79, 209, 197, 0.25);
  transform: translateX(2px);
  background: rgba(10, 16, 28, 0.65);
}

.key-row--active {
  border-color: rgba(79, 209, 197, 0.55);
  background: linear-gradient(130deg, rgba(79, 209, 197, 0.18), rgba(58, 169, 255, 0.08));
  box-shadow: inset 0 0 0 1px rgba(79, 209, 197, 0.18);
}

.key-meta {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.key-detail {
  gap: 18px;
}

.key-summary {
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid rgba(120, 160, 220, 0.18);
  background: linear-gradient(135deg, rgba(10, 18, 30, 0.88), rgba(7, 12, 22, 0.75));
  box-shadow: inset 0 0 12px rgba(79, 209, 197, 0.06);
}

.key-summary-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}

.key-summary-label {
  font-size: 16px;
  font-weight: 600;
  color: #e6f6ff;
  text-shadow: 0 0 12px rgba(79, 209, 197, 0.25);
}

.key-summary-id {
  margin-top: 4px;
  font-size: 11px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: rgba(176, 214, 244, 0.75);
}

.key-summary-id span {
  display: inline-block;
  margin-left: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  letter-spacing: 0.3px;
  text-transform: none;
  color: rgba(210, 232, 255, 0.96);
  word-break: break-all;
}

.key-summary-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.key-badge {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(120, 160, 220, 0.2);
  background: rgba(10, 16, 28, 0.7);
  font-size: 11px;
  color: rgba(214, 236, 255, 0.92);
  box-shadow: inset 0 0 10px rgba(79, 209, 197, 0.08);
}

.key-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.key-detail-section {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(120, 160, 220, 0.16);
  background: rgba(8, 14, 24, 0.6);
  box-shadow: inset 0 0 10px rgba(79, 209, 197, 0.04);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.key-detail-section .section-title {
  color: rgba(176, 214, 244, 0.85);
}

.key-constraint {
  font-size: 13px;
  color: rgba(220, 238, 255, 0.96);
}

.key-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(120, 160, 220, 0.18);
  background: rgba(8, 14, 24, 0.7);
}

.key-actions .section-title {
  margin: 0;
}

.key-actions .el-button {
  border-color: rgba(79, 209, 197, 0.35);
  color: #8ff5ea;
}

.token-row--current {
  border-color: rgba(79, 209, 197, 0.6);
  box-shadow: inset 0 0 0 1px rgba(79, 209, 197, 0.35);
  background: rgba(12, 24, 32, 0.75);
}

.token-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.token-label-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.token-label {
  font-weight: 600;
  color: rgba(224, 242, 255, 0.96);
  text-shadow: 0 0 8px rgba(79, 209, 197, 0.2);
}

.token-owner {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(120, 160, 220, 0.25);
  color: var(--hub-muted);
  background: rgba(18, 26, 38, 0.7);
  white-space: nowrap;
}

.token-owner--org {
  border-color: rgba(79, 209, 197, 0.35);
  color: var(--hub-accent);
  background: rgba(79, 209, 197, 0.14);
}

.token-meta {
  font-size: 12px;
  color: var(--hub-muted);
}

.token-meta--wrap {
  word-break: break-word;
  line-height: 1.4;
}

.token-scopes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.token-scopes .el-tag {
  background: rgba(18, 26, 38, 0.85);
  border-color: rgba(120, 160, 220, 0.25);
  color: rgba(188, 206, 236, 0.82);
}

.token-scopes .el-tag.el-tag--info {
  background: rgba(18, 26, 38, 0.85);
  border-color: rgba(120, 160, 220, 0.25);
  color: rgba(188, 206, 236, 0.82);
}

.form-hint {
  font-size: 11px;
  color: var(--hub-muted);
  margin-top: -4px;
}

.form-hint--error {
  color: #ffb4b4;
}

.auth-dialog .el-dialog {
  background: rgba(7, 12, 22, 0.95);
  border: 1px solid rgba(120, 160, 220, 0.2);
  border-radius: 20px;
  box-shadow: 0 24px 60px rgba(7, 12, 22, 0.6);
}

.edit-dialog .el-dialog {
  background: rgba(7, 12, 22, 0.95);
  border: 1px solid rgba(120, 160, 220, 0.2);
  border-radius: 20px;
  box-shadow: 0 24px 60px rgba(7, 12, 22, 0.6);
}

.create-key-dialog {
  background: linear-gradient(160deg, rgba(10, 16, 28, 0.96), rgba(7, 12, 22, 0.9));
  border: 1px solid rgba(120, 160, 220, 0.18);
  border-radius: 20px;
  box-shadow: 0 24px 60px rgba(4, 8, 18, 0.6), inset 0 0 18px rgba(79, 209, 197, 0.06);
}

.create-key-dialog .el-dialog__body {
  padding: 0 24px 20px;
}

.create-key-dialog .el-dialog__header {
  margin-right: 0;
  padding: 20px 24px 0;
}

.create-key-dialog .el-form-item__label {
  color: var(--hub-muted);
}

.create-key-dialog .el-input__wrapper {
  background-color: rgba(9, 16, 28, 0.85);
  border: 1px solid rgba(120, 160, 220, 0.2);
  box-shadow: none;
}

.create-key-dialog .el-input__inner {
  color: var(--hub-text);
}

.create-key-dialog .el-input__inner::placeholder {
  color: rgba(154, 172, 204, 0.7);
}

.hub-message-box {
  background: linear-gradient(160deg, rgba(10, 16, 28, 0.98), rgba(7, 12, 22, 0.95));
  border: 1px solid rgba(120, 160, 220, 0.22);
  border-radius: 18px;
  box-shadow: 0 24px 60px rgba(4, 8, 18, 0.55), inset 0 0 18px rgba(79, 209, 197, 0.06);
  color: var(--hub-text);
}

.hub-message-box .el-message-box__title {
  color: var(--hub-text);
  font-weight: 600;
}

.hub-message-box .el-message-box__content {
  color: var(--hub-muted);
}

.hub-message-box .el-message-box__message {
  color: inherit;
}

.hub-message-box .el-message-box__btns {
  padding-top: 4px;
}

.hub-message-box .el-button {
  background: rgba(9, 16, 28, 0.8);
  border: 1px solid rgba(120, 160, 220, 0.2);
  color: var(--hub-text);
}

.hub-message-box .el-button:hover {
  border-color: rgba(79, 209, 197, 0.5);
  color: var(--hub-text);
}

.hub-message-box .el-button--primary {
  background: linear-gradient(135deg, rgba(79, 209, 197, 0.9), rgba(58, 169, 255, 0.85));
  border-color: transparent;
  color: #07121c;
  font-weight: 600;
}

.hub-message-box .el-message-box__status {
  color: rgba(255, 184, 77, 0.9);
}

.auth-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.auth-eyebrow {
  text-transform: uppercase;
  letter-spacing: 2px;
  font-size: 11px;
  color: var(--hub-accent-2);
}

.auth-form {
  margin-top: 16px;
}

.auth-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@keyframes hero-fade {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes card-rise {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .public-hero,
  .public-card {
    animation: none;
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 1180px) {
  .hub-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-left,
  .header-right {
    width: 100%;
  }

  .header-right {
    margin-left: 0;
    justify-content: space-between;
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .status-panel {
    flex-direction: column;
    align-items: flex-start;
  }

  .status-cards {
    width: 100%;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }

  .workspace-body {
    grid-template-columns: 1fr;
  }

  .console-shell {
    flex-direction: column;
  }

  .console-nav {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 10px;
    flex: 0 0 auto;
  }

  .console-nav-group {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .console-nav-item {
    width: auto;
  }

  .header-nav {
    width: 100%;
    flex-wrap: wrap;
  }

  .public-hero {
    grid-template-columns: 1fr;
  }

  .public-layout {
    grid-template-columns: 1fr;
  }

  .account-layout {
    grid-template-columns: 1fr;
  }

  .session-layout {
    grid-template-columns: 1fr;
  }

  .session-detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .hub-header {
    padding: 16px 20px;
    gap: 12px;
  }

  .header-left,
  .header-right {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .brand {
    gap: 12px;
  }

  .brand-mark {
    width: 34px;
    height: 34px;
    border-radius: 12px;
  }

  .brand-title {
    font-size: 16px;
  }

  .brand-subtitle {
    display: none;
  }

  .header-search {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .header-search .el-button {
    width: 100%;
  }

  .header-nav {
    width: 100%;
    justify-content: flex-start;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 6px;
    -webkit-overflow-scrolling: touch;
  }

  .nav-link {
    white-space: nowrap;
  }

  .header-actions {
    width: 100%;
    justify-content: stretch;
  }

  .header-actions .el-button {
    width: 100%;
  }

  .account-trigger {
    width: 100%;
    justify-content: space-between;
  }

  .hub-main {
    padding: 24px 20px 72px;
  }

  .hub-input {
    width: 100%;
  }

  .hub-search {
    width: 100%;
  }

  .public-hero {
    padding: 20px;
  }

  .public-search {
    flex-direction: column;
    align-items: stretch;
  }

  .public-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .pagination {
    justify-content: center;
  }

  .auth-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
}
</style>
