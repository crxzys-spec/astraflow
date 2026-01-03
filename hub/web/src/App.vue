<template>
  <div class="hub-app">
    <div class="ambient-grid"></div>
    <header class="hub-header">
      <div class="brand">
        <span class="brand-mark">A</span>
        <div>
          <div class="brand-title">AstraFlow Hub</div>
          <div class="brand-subtitle">Secure discovery for packages and workflows.</div>
        </div>
      </div>
      <div class="header-actions">
        <el-input
          v-model="apiBase"
          class="hub-input"
          placeholder="API base (http://localhost:8310)"
        />
        <el-input
          v-model="tokenInput"
          class="hub-input"
          placeholder="Bearer token"
          type="password"
          show-password
        />
        <el-button type="primary" @click="applyAuth">Connect</el-button>
        <el-button plain @click="openAuthDialog">Login / Register</el-button>
      </div>
    </header>

    <main class="hub-main">
      <section class="status-panel">
        <div>
          <div class="status-eyebrow">Connection</div>
          <h1>Hub console</h1>
          <p class="status-subtitle">
            Authenticate to browse packages and workflows, then drill into detail
            snapshots and version histories.
          </p>
        </div>
        <div class="status-cards">
          <div class="status-card">
            <div class="status-label">Packages indexed</div>
            <div class="status-value">{{ packageTotalDisplay }}</div>
          </div>
          <div class="status-card">
            <div class="status-label">Workflows indexed</div>
            <div class="status-value">{{ workflowTotalDisplay }}</div>
          </div>
          <div class="status-card">
            <div class="status-label">Session</div>
            <div class="status-value">
              <span class="status-pill" :class="{ ready: hasToken }">
                {{ hasToken ? 'Authenticated' : 'Token required' }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section class="workspace">
        <div class="workspace-header">
          <el-tabs v-model="activeTab" class="hub-tabs">
            <el-tab-pane label="Packages" name="packages" />
            <el-tab-pane label="Workflows" name="workflows" />
            <el-tab-pane label="Organizations" name="orgs" />
          </el-tabs>
          <div class="filters">
            <el-input v-model="searchQuery" placeholder="Search" clearable />
            <el-input v-model="tagFilter" placeholder="Tag" clearable />
            <el-input v-model="ownerFilter" placeholder="Owner" clearable />
            <el-button type="primary" @click="applyFilters">Search</el-button>
            <el-button plain @click="resetFilters">Reset</el-button>
          </div>
        </div>

        <el-alert
          v-if="listError"
          class="hub-alert"
          type="error"
          show-icon
          :closable="false"
          :title="listError"
        />

        <div class="workspace-body">
          <div class="list-pane">
            <el-skeleton v-if="listLoading" animated :rows="6" />
            <template v-else>
              <div v-if="activeTab === 'packages'" class="card-grid">
                <el-card
                  v-for="pkg in packages"
                  :key="pkg.name"
                  class="hub-card"
                  shadow="never"
                  @click="selectPackage(pkg)"
                >
                  <div class="card-head">
                    <div>
                      <div class="card-title">{{ pkg.name }}</div>
                      <div class="card-meta">
                        v{{ pkg.latestVersion || 'n/a' }} · {{ pkg.ownerName || 'Unknown' }}
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

              <div v-else-if="activeTab === 'workflows'" class="card-grid workflows">
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
                        {{ flow.ownerName || 'Unknown' }} · {{ formatDate(flow.updatedAt) }}
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

              <div v-else class="card-grid orgs">
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
                v-model:current-page="page"
                v-model:page-size="pageSize"
                layout="sizes, prev, pager, next"
                :page-sizes="[6, 12, 24, 48]"
                :total="activeTotal"
                @current-change="loadList"
                @size-change="handlePageSize"
              />
            </div>
          </div>

          <aside class="detail-pane">
            <div class="detail-card">
              <div class="detail-header">
                <div>
                  <div class="detail-eyebrow">Details</div>
                  <h3>{{ detailTitle }}</h3>
                </div>
                <el-button
                  v-if="detailTitle !== 'Select an item'"
                  size="small"
                  plain
                  @click="clearSelection"
                >
                  Clear
                </el-button>
              </div>

              <el-skeleton v-if="detailLoading" animated :rows="8" />
              <el-alert
                v-else-if="detailError"
                type="error"
                show-icon
                :closable="false"
                :title="detailError"
              />
              <div v-else-if="selectedPackage" class="detail-body">
                <div class="detail-meta">
                  <div>
                    <span class="meta-label">Owner</span>
                    <span>{{ selectedPackage.ownerName || selectedPackage.ownerId }}</span>
                  </div>
                  <div>
                    <span class="meta-label">Visibility</span>
                    <span>{{ selectedPackage.visibility || 'public' }}</span>
                  </div>
                  <div>
                    <span class="meta-label">Updated</span>
                    <span>{{ formatDate(selectedPackage.updatedAt) }}</span>
                  </div>
                </div>
                <p class="detail-text">{{ selectedPackage.description || 'No description.' }}</p>
                <div class="detail-tags">
                  <el-tag v-for="tag in selectedPackage.tags || []" :key="tag" size="small">
                    {{ tag }}
                  </el-tag>
                </div>
                <div class="detail-section">
                  <div class="section-title">Versions</div>
                  <div class="version-list">
                    <span v-for="ver in selectedPackage.versions" :key="ver" class="version-pill">
                      {{ ver }}
                    </span>
                  </div>
                </div>
                <div v-if="selectedPackage.readme" class="detail-section">
                  <div class="section-title">Readme</div>
                  <pre class="detail-readme">{{ selectedPackage.readme }}</pre>
                </div>
              </div>

              <div v-else-if="selectedWorkflow" class="detail-body">
                <div class="detail-meta">
                  <div>
                    <span class="meta-label">Owner</span>
                    <span>{{ selectedWorkflow.ownerName || selectedWorkflow.ownerId }}</span>
                  </div>
                  <div>
                    <span class="meta-label">Visibility</span>
                    <span>{{ selectedWorkflow.visibility || 'public' }}</span>
                  </div>
                  <div>
                    <span class="meta-label">Updated</span>
                    <span>{{ formatDate(selectedWorkflow.updatedAt) }}</span>
                  </div>
                </div>
                <p class="detail-text">{{ selectedWorkflow.summary || selectedWorkflow.description || 'No summary.' }}</p>
                <div class="detail-tags">
                  <el-tag v-for="tag in selectedWorkflow.tags || []" :key="tag" size="small" type="info">
                    {{ tag }}
                  </el-tag>
                </div>
                <div v-if="workflowPreviewSrc" class="detail-section">
                  <div class="section-title">Preview</div>
                  <div class="workflow-preview">
                    <img :src="workflowPreviewSrc" :alt="`${selectedWorkflow.name} preview`" />
                  </div>
                </div>
                <div class="detail-section">
                  <div class="section-title">Versions</div>
                  <div class="version-stack">
                    <div
                      v-for="ver in workflowVersions"
                      :key="ver.id"
                      class="version-row"
                      :class="{ 'version-row--active': selectedWorkflowVersion && selectedWorkflowVersion.id === ver.id }"
                      @click="selectWorkflowVersion(ver)"
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
                  <div v-if="workflowVersionLoading" class="detail-empty">
                    Loading dependencies...
                  </div>
                  <div v-else-if="workflowVersionError" class="detail-empty">
                    {{ workflowVersionError }}
                  </div>
                  <div v-else-if="workflowDependencies.length" class="dependency-list">
                    <span
                      v-for="dep in workflowDependencies"
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

              <div v-else-if="selectedOrg" class="detail-body">
                <div class="detail-meta">
                  <div>
                    <span class="meta-label">Owner</span>
                    <span>{{ selectedOrg.ownerId }}</span>
                  </div>
                  <div>
                    <span class="meta-label">Slug</span>
                    <span>{{ selectedOrg.slug }}</span>
                  </div>
                  <div>
                    <span class="meta-label">Updated</span>
                    <span>{{ formatDate(selectedOrg.updatedAt) }}</span>
                  </div>
                </div>
                <div class="detail-section">
                  <div class="section-title">Teams</div>
                  <el-skeleton v-if="teamsLoading" animated :rows="4" />
                  <el-alert
                    v-else-if="teamsError"
                    type="error"
                    show-icon
                    :closable="false"
                    :title="teamsError"
                  />
                  <div v-else class="team-list">
                    <div v-if="teams.length === 0" class="detail-empty">
                      No teams yet.
                    </div>
                    <div v-else>
                      <div v-for="team in teams" :key="team.id" class="team-row">
                        <div>
                          <div class="team-name">{{ team.name }}</div>
                          <div class="team-meta">Slug {{ team.slug }}</div>
                        </div>
                        <el-button size="small" plain @click="openTeamEdit(team)">
                          Edit
                        </el-button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="detail-empty">
                <p>Select a package, workflow, or organization to see details.</p>
              </div>
            </div>
          </aside>
        </div>
      </section>
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
            <h3>Edit organization</h3>
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
            Save
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="teamEditOpen"
      width="420px"
      class="edit-dialog"
      :show-close="false"
    >
      <template #header>
        <div class="auth-header">
          <div>
            <div class="auth-eyebrow">Team</div>
            <h3>Edit team</h3>
          </div>
          <el-button text @click="teamEditOpen = false">Close</el-button>
        </div>
      </template>

      <el-form label-position="top" class="auth-form">
        <el-form-item label="Name">
          <el-input v-model="teamEditForm.name" />
        </el-form-item>
        <el-form-item label="Slug">
          <el-input v-model="teamEditForm.slug" />
        </el-form-item>
      </el-form>

      <el-alert
        v-if="teamEditError"
        type="error"
        show-icon
        :closable="false"
        :title="teamEditError"
      />

      <template #footer>
        <div class="auth-footer">
          <el-button plain @click="teamEditOpen = false">Cancel</el-button>
          <el-button type="primary" :loading="teamEditLoading" @click="submitTeamEdit">
            Save
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'

interface PageMeta {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

interface PackageSummary {
  name: string
  latestVersion?: string
  description?: string
  tags?: string[]
  ownerName?: string
  visibility?: string
  updatedAt?: string
}

interface PackageDetail {
  name: string
  description?: string
  readme?: string
  versions: string[]
  distTags?: Record<string, string>
  tags?: string[]
  ownerId?: string
  ownerName?: string
  updatedAt?: string
  visibility?: string
}

interface WorkflowSummary {
  id: string
  name: string
  summary?: string
  description?: string
  tags?: string[]
  ownerName?: string
  updatedAt?: string
  latestVersion?: string
  visibility?: string
}

interface WorkflowDetail {
  id: string
  name: string
  summary?: string
  description?: string
  tags?: string[]
  ownerId?: string
  ownerName?: string
  updatedAt?: string
  visibility?: string
  previewImage?: string
}

interface WorkflowVersionSummary {
  id: string
  version: string
  publishedAt?: string
  changelog?: string
}

interface PackageDependency {
  name: string
  version: string
}

interface WorkflowVersionDetail {
  id: string
  version: string
  summary?: string
  description?: string
  tags?: string[]
  previewImage?: string
  dependencies?: PackageDependency[]
  publishedAt?: string
  publisherId?: string
}

interface Organization {
  id: string
  name: string
  slug: string
  ownerId: string
  createdAt?: string
  updatedAt?: string
}

interface Team {
  id: string
  orgId: string
  name: string
  slug: string
  createdAt?: string
}

interface AuthResponse {
  token: { token?: string }
}

const storageKeys = {
  apiBase: 'hub_api_base',
  token: 'hub_auth_token'
}

const apiBase = ref(localStorage.getItem(storageKeys.apiBase) || 'http://localhost:8310')
const tokenInput = ref(localStorage.getItem(storageKeys.token) || '')
const authToken = ref(tokenInput.value)

type HubTab = 'packages' | 'workflows' | 'orgs'
type HubSelection = { tab: HubTab; id: string }

const resolveInitialTab = (): HubTab => {
  if (typeof window === 'undefined') {
    return 'packages'
  }
  const tab = new URLSearchParams(window.location.search).get('tab')
  if (tab === 'workflows' || tab === 'orgs' || tab === 'packages') {
    return tab
  }
  return 'packages'
}

const resolveInitialSelection = (defaultTab: HubTab): HubSelection | null => {
  if (typeof window === 'undefined') {
    return null
  }
  const params = new URLSearchParams(window.location.search)
  const id = params.get('id')?.trim()
  if (!id) {
    return null
  }
  const tab = params.get('tab')
  if (tab === 'workflows' || tab === 'orgs' || tab === 'packages') {
    return { tab, id }
  }
  return { tab: defaultTab, id }
}

const initialTab = resolveInitialTab()
const activeTab = ref<HubTab>(initialTab)
const pendingSelection = ref<HubSelection | null>(resolveInitialSelection(initialTab))
const searchQuery = ref('')
const tagFilter = ref('')
const ownerFilter = ref('')
const page = ref(1)
const pageSize = ref(12)

const listLoading = ref(false)
const detailLoading = ref(false)
const listError = ref('')
const detailError = ref('')

const packages = ref<PackageSummary[]>([])
const workflows = ref<WorkflowSummary[]>([])
const packageTotal = ref<number | null>(null)
const workflowTotal = ref<number | null>(null)
const organizations = ref<Organization[]>([])
const orgTotal = ref<number | null>(null)

const selectedPackage = ref<PackageDetail | null>(null)
const selectedWorkflow = ref<WorkflowDetail | null>(null)
const selectedOrg = ref<Organization | null>(null)
const workflowVersions = ref<WorkflowVersionSummary[]>([])
const selectedWorkflowVersion = ref<WorkflowVersionDetail | null>(null)
const workflowVersionLoading = ref(false)
const workflowVersionError = ref('')
const teams = ref<Team[]>([])
const teamsLoading = ref(false)
const teamsError = ref('')

const authDialogOpen = ref(false)
const authMode = ref<'login' | 'register'>('login')
const authLoading = ref(false)
const authError = ref('')
const authForm = reactive({
  username: '',
  password: '',
  displayName: '',
  email: ''
})

const orgEditOpen = ref(false)
const orgEditLoading = ref(false)
const orgEditError = ref('')
const orgEditTarget = ref<Organization | null>(null)
const orgEditForm = reactive({
  name: '',
  slug: ''
})

const teamEditOpen = ref(false)
const teamEditLoading = ref(false)
const teamEditError = ref('')
const teamEditTarget = ref<Team | null>(null)
const teamEditForm = reactive({
  name: '',
  slug: ''
})

const hasToken = computed(() => Boolean(authToken.value))
const activeTotal = computed(() => {
  const total =
    activeTab.value === 'packages'
      ? packageTotal.value
      : activeTab.value === 'workflows'
        ? workflowTotal.value
        : orgTotal.value
  return total ?? 0
})
const hasListData = computed(() => {
  if (activeTab.value === 'packages') return packages.value.length > 0
  if (activeTab.value === 'workflows') return workflows.value.length > 0
  return organizations.value.length > 0
})
const packageTotalDisplay = computed(() => (packageTotal.value === null ? '--' : packageTotal.value.toString()))
const workflowTotalDisplay = computed(() => (workflowTotal.value === null ? '--' : workflowTotal.value.toString()))
const detailTitle = computed(() => {
  if (selectedPackage.value) return selectedPackage.value.name
  if (selectedWorkflow.value) return selectedWorkflow.value.name
  if (selectedOrg.value) return selectedOrg.value.name
  return 'Select an item'
})
const workflowPreviewSrc = computed(() => {
  const raw = selectedWorkflowVersion.value?.previewImage || selectedWorkflow.value?.previewImage
  if (!raw) return ''
  return raw.startsWith('data:') ? raw : `data:image/png;base64,${raw}`
})
const workflowDependencies = computed(() => selectedWorkflowVersion.value?.dependencies || [])

function normalizeBase(base: string) {
  return base.replace(/\/$/, '')
}

function openAuthDialog() {
  authDialogOpen.value = true
  authError.value = ''
}

function resetAuthForm() {
  authForm.username = ''
  authForm.password = ''
  authForm.displayName = ''
  authForm.email = ''
  authError.value = ''
}

function applyAuth() {
  const token = tokenInput.value.trim()
  authToken.value = token
  localStorage.setItem(storageKeys.apiBase, apiBase.value)
  if (token) {
    localStorage.setItem(storageKeys.token, token)
  } else {
    localStorage.removeItem(storageKeys.token)
  }
  loadList()
}

function clearAuth() {
  tokenInput.value = ''
  authToken.value = ''
  localStorage.removeItem(storageKeys.token)
  listError.value = 'Token required to load hub data.'
  packages.value = []
  workflows.value = []
  packageTotal.value = null
  workflowTotal.value = null
  organizations.value = []
  orgTotal.value = null
  clearSelection()
}

function clearSelection() {
  selectedPackage.value = null
  selectedWorkflow.value = null
  selectedOrg.value = null
  workflowVersions.value = []
  selectedWorkflowVersion.value = null
  workflowVersionLoading.value = false
  workflowVersionError.value = ''
  teams.value = []
  teamsError.value = ''
}

function buildQuery() {
  const params = new URLSearchParams()
  if (searchQuery.value) params.set('q', searchQuery.value)
  if (tagFilter.value) params.set('tag', tagFilter.value)
  if (ownerFilter.value) params.set('owner', ownerFilter.value)
  params.set('page', String(page.value))
  params.set('pageSize', String(pageSize.value))
  return params.toString()
}

async function tryAutoSelectFromQuery(tab: HubTab) {
  const selection = pendingSelection.value
  if (!selection || selection.tab !== tab) {
    return
  }
  pendingSelection.value = null
  if (tab === 'packages') {
    await loadPackageDetail(selection.id)
    return
  }
  if (tab === 'workflows') {
    await loadWorkflowDetails(selection.id)
    return
  }
  if (tab === 'orgs') {
    const match = organizations.value.find((org) => org.id === selection.id || org.slug === selection.id)
    if (match) {
      await selectOrganization(match)
    }
  }
}

async function requestJson<T>(path: string, options: RequestInit = {}) {
  if (!authToken.value) {
    throw new Error('Token required to call hub API.')
  }
  const url = `${normalizeBase(apiBase.value)}${path}`
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  headers.set('Authorization', `Bearer ${authToken.value}`)
  const response = await fetch(url, { ...options, headers })
  if (!response.ok) {
    const message = response.status === 401
      ? 'Unauthorized. Check your token.'
      : `Request failed (${response.status})`
    throw new Error(message)
  }
  return (await response.json()) as T
}

async function requestAuth(path: string, body: Record<string, unknown>) {
  const url = `${normalizeBase(apiBase.value)}${path}`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify(body)
  })
  if (!response.ok) {
    const message = response.status === 401
      ? 'Invalid credentials.'
      : response.status === 409
        ? 'Username already exists.'
        : `Request failed (${response.status})`
    throw new Error(message)
  }
  return (await response.json()) as AuthResponse
}

async function submitAuth() {
  authError.value = ''
  if (!authForm.username || !authForm.password) {
    authError.value = 'Username and password are required.'
    return
  }
  authLoading.value = true
  try {
    const payload = authMode.value === 'login'
      ? { username: authForm.username, password: authForm.password }
      : {
          username: authForm.username,
          password: authForm.password,
          displayName: authForm.displayName || undefined,
          email: authForm.email || undefined
        }
    const response = await requestAuth(
      authMode.value === 'login' ? '/api/v1/auth/login' : '/api/v1/auth/register',
      payload
    )
    const token = response.token?.token
    if (!token) {
      throw new Error('Token missing from response.')
    }
    tokenInput.value = token
    authToken.value = token
    localStorage.setItem(storageKeys.token, token)
    localStorage.setItem(storageKeys.apiBase, apiBase.value)
    authDialogOpen.value = false
    await loadList()
  } catch (error) {
    authError.value = (error as Error).message
  } finally {
    authLoading.value = false
  }
}

async function loadPackages() {
  listLoading.value = true
  listError.value = ''
  try {
    const data = await requestJson<{ items: PackageSummary[]; meta: PageMeta }>(
      `/api/v1/packages?${buildQuery()}`
    )
    packages.value = data.items || []
    packageTotal.value = data.meta?.total || 0
    void tryAutoSelectFromQuery('packages')
  } catch (error) {
    listError.value = (error as Error).message
    packageTotal.value = null
    if ((error as Error).message.includes('Unauthorized')) {
      authDialogOpen.value = true
    }
  } finally {
    listLoading.value = false
  }
}

async function loadWorkflows() {
  listLoading.value = true
  listError.value = ''
  try {
    const data = await requestJson<{ items: WorkflowSummary[]; meta: PageMeta }>(
      `/api/v1/workflows?${buildQuery()}`
    )
    workflows.value = data.items || []
    workflowTotal.value = data.meta?.total || 0
    void tryAutoSelectFromQuery('workflows')
  } catch (error) {
    listError.value = (error as Error).message
    workflowTotal.value = null
    if ((error as Error).message.includes('Unauthorized')) {
      authDialogOpen.value = true
    }
  } finally {
    listLoading.value = false
  }
}

async function loadOrganizations() {
  listLoading.value = true
  listError.value = ''
  try {
    const data = await requestJson<{ items: Organization[] }>(
      '/api/v1/orgs'
    )
    const items = data.items || []
    const query = searchQuery.value.trim().toLowerCase()
    const owner = ownerFilter.value.trim().toLowerCase()
    const filtered = items.filter((org) => {
      const matchesQuery = !query
        || org.name.toLowerCase().includes(query)
        || org.slug.toLowerCase().includes(query)
      const matchesOwner = !owner
        || org.ownerId.toLowerCase().includes(owner)
      return matchesQuery && matchesOwner
    })
    orgTotal.value = filtered.length
    const start = (page.value - 1) * pageSize.value
    organizations.value = filtered.slice(start, start + pageSize.value)
    void tryAutoSelectFromQuery('orgs')
  } catch (error) {
    listError.value = (error as Error).message
    orgTotal.value = null
    if ((error as Error).message.includes('Unauthorized')) {
      authDialogOpen.value = true
    }
  } finally {
    listLoading.value = false
  }
}

async function loadList() {
  if (!authToken.value) {
    listError.value = 'Token required to load hub data.'
    authDialogOpen.value = true
    return
  }
  clearSelection()
  if (activeTab.value === 'packages') {
    await loadPackages()
  } else if (activeTab.value === 'workflows') {
    await loadWorkflows()
  } else {
    await loadOrganizations()
  }
}

async function loadPackageDetail(packageName: string) {
  detailLoading.value = true
  detailError.value = ''
  selectedWorkflow.value = null
  workflowVersions.value = []
  selectedWorkflowVersion.value = null
  workflowVersionLoading.value = false
  workflowVersionError.value = ''
  selectedOrg.value = null
  teams.value = []
  teamsError.value = ''
  try {
    const detail = await requestJson<PackageDetail>(
      `/api/v1/packages/${encodeURIComponent(packageName)}`
    )
    selectedPackage.value = detail
  } catch (error) {
    detailError.value = (error as Error).message
  } finally {
    detailLoading.value = false
  }
}

async function selectPackage(pkg: PackageSummary) {
  await loadPackageDetail(pkg.name)
}

async function loadWorkflowVersionDetail(workflowId: string, versionId?: string) {
  if (!versionId) {
    selectedWorkflowVersion.value = null
    return
  }
  workflowVersionLoading.value = true
  workflowVersionError.value = ''
  try {
    const detail = await requestJson<WorkflowVersionDetail>(
      `/api/v1/workflows/${encodeURIComponent(workflowId)}/versions/${encodeURIComponent(versionId)}`
    )
    selectedWorkflowVersion.value = detail
  } catch (error) {
    workflowVersionError.value = (error as Error).message
    selectedWorkflowVersion.value = null
  } finally {
    workflowVersionLoading.value = false
  }
}

async function selectWorkflowVersion(version: WorkflowVersionSummary) {
  if (!selectedWorkflow.value) {
    return
  }
  await loadWorkflowVersionDetail(selectedWorkflow.value.id, version.id)
}

async function loadWorkflowDetails(workflowId: string) {
  detailLoading.value = true
  detailError.value = ''
  selectedPackage.value = null
  workflowVersions.value = []
  selectedWorkflowVersion.value = null
  workflowVersionLoading.value = false
  workflowVersionError.value = ''
  selectedOrg.value = null
  teams.value = []
  teamsError.value = ''
  try {
    const detail = await requestJson<WorkflowDetail>(
      `/api/v1/workflows/${encodeURIComponent(workflowId)}`
    )
    const versions = await requestJson<{ items: WorkflowVersionSummary[] }>(
      `/api/v1/workflows/${encodeURIComponent(workflowId)}/versions`
    )
    selectedWorkflow.value = detail
    workflowVersions.value = versions.items || []
    if (workflowVersions.value.length > 0) {
      void loadWorkflowVersionDetail(detail.id, workflowVersions.value[0].id)
    }
  } catch (error) {
    detailError.value = (error as Error).message
  } finally {
    detailLoading.value = false
  }
}

async function selectWorkflow(flow: WorkflowSummary) {
  await loadWorkflowDetails(flow.id)
}

async function loadTeams(orgId: string) {
  teamsLoading.value = true
  teamsError.value = ''
  try {
    const data = await requestJson<{ items: Team[] }>(
      `/api/v1/orgs/${encodeURIComponent(orgId)}/teams`
    )
    teams.value = data.items || []
  } catch (error) {
    teamsError.value = (error as Error).message
    teams.value = []
  } finally {
    teamsLoading.value = false
  }
}

async function selectOrganization(org: Organization) {
  detailLoading.value = true
  detailError.value = ''
  selectedPackage.value = null
  selectedWorkflow.value = null
  workflowVersions.value = []
  selectedWorkflowVersion.value = null
  workflowVersionLoading.value = false
  workflowVersionError.value = ''
  selectedOrg.value = org
  teams.value = []
  teamsError.value = ''
  try {
    await loadTeams(org.id)
  } finally {
    detailLoading.value = false
  }
}

function openOrgEdit(org: Organization) {
  orgEditTarget.value = org
  orgEditForm.name = org.name
  orgEditForm.slug = org.slug
  orgEditError.value = ''
  orgEditOpen.value = true
}

async function submitOrgEdit() {
  if (!orgEditTarget.value) {
    orgEditError.value = 'Select an organization to edit.'
    return
  }
  const original = orgEditTarget.value
  const name = orgEditForm.name.trim()
  const slug = orgEditForm.slug.trim()
  if (!name) {
    orgEditError.value = 'Name is required.'
    return
  }
  if (!slug) {
    orgEditError.value = 'Slug is required.'
    return
  }
  if (slug !== original.slug) {
    try {
      await ElMessageBox.confirm(
        'Changing the slug will change IDs and invalidate old links. Continue?',
        'Confirm slug change',
        {
          confirmButtonText: 'Change slug',
          cancelButtonText: 'Cancel',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }
  const payload: Record<string, string> = {}
  if (name && name !== original.name) payload.name = name
  if (slug && slug !== original.slug) payload.slug = slug
  if (!Object.keys(payload).length) {
    orgEditError.value = 'No changes to save.'
    return
  }
  orgEditLoading.value = true
  orgEditError.value = ''
  try {
    const updated = await requestJson<Organization>(
      `/api/v1/orgs/${encodeURIComponent(original.id)}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }
    )
    if (selectedOrg.value && selectedOrg.value.id === original.id) {
      selectedOrg.value = updated
      await loadTeams(updated.id)
    }
    await loadOrganizations()
    orgEditOpen.value = false
    orgEditTarget.value = null
  } catch (error) {
    orgEditError.value = (error as Error).message
  } finally {
    orgEditLoading.value = false
  }
}

function openTeamEdit(team: Team) {
  teamEditTarget.value = team
  teamEditForm.name = team.name
  teamEditForm.slug = team.slug
  teamEditError.value = ''
  teamEditOpen.value = true
}

async function submitTeamEdit() {
  if (!teamEditTarget.value) {
    teamEditError.value = 'Select a team to edit.'
    return
  }
  const original = teamEditTarget.value
  const name = teamEditForm.name.trim()
  const slug = teamEditForm.slug.trim()
  if (!name) {
    teamEditError.value = 'Name is required.'
    return
  }
  if (!slug) {
    teamEditError.value = 'Slug is required.'
    return
  }
  if (slug !== original.slug) {
    try {
      await ElMessageBox.confirm(
        'Changing the slug will change IDs and invalidate old links. Continue?',
        'Confirm slug change',
        {
          confirmButtonText: 'Change slug',
          cancelButtonText: 'Cancel',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }
  const payload: Record<string, string> = {}
  if (name && name !== original.name) payload.name = name
  if (slug && slug !== original.slug) payload.slug = slug
  if (!Object.keys(payload).length) {
    teamEditError.value = 'No changes to save.'
    return
  }
  teamEditLoading.value = true
  teamEditError.value = ''
  try {
    const updated = await requestJson<Team>(
      `/api/v1/orgs/${encodeURIComponent(original.orgId)}/teams/${encodeURIComponent(original.id)}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }
    )
    if (selectedOrg.value && selectedOrg.value.id === original.orgId) {
      await loadTeams(selectedOrg.value.id)
    }
    teamEditOpen.value = false
    teamEditTarget.value = null
  } catch (error) {
    teamEditError.value = (error as Error).message
  } finally {
    teamEditLoading.value = false
  }
}

function handlePageSize() {
  page.value = 1
  loadList()
}

function applyFilters() {
  page.value = 1
  loadList()
}

function resetFilters() {
  searchQuery.value = ''
  tagFilter.value = ''
  ownerFilter.value = ''
  page.value = 1
  loadList()
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

watch(activeTab, () => {
  page.value = 1
  loadList()
})

onMounted(() => {
  if (authToken.value) {
    loadList()
  } else {
    listError.value = 'Token required to load hub data.'
  }
})
</script>

<style scoped>
.hub-app {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  padding-bottom: 80px;
}

.hub-app::before,
.hub-app::after {
  content: '';
  position: absolute;
  inset: -20% -10% auto -10%;
  height: 70%;
  background: radial-gradient(circle at top, rgba(79, 209, 197, 0.22), transparent 60%),
    radial-gradient(circle at 40% 20%, rgba(255, 184, 77, 0.18), transparent 55%);
  pointer-events: none;
  z-index: 0;
}

.hub-app::after {
  inset: auto -10% -40% -10%;
  height: 80%;
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

.hub-main {
  position: relative;
  z-index: 1;
  padding: 32px 48px 0;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.status-panel {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
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
  background: var(--hub-surface);
  border: 1px solid var(--hub-border);
  box-shadow: inset 0 0 24px rgba(79, 209, 197, 0.06);
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
  background: rgba(10, 16, 28, 0.6);
  border: 1px solid rgba(120, 160, 220, 0.2);
  border-radius: 24px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.filters {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.hub-alert {
  margin-bottom: 4px;
}

.workspace-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 360px);
  gap: 24px;
}

.list-pane {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.hub-card {
  background: var(--hub-surface);
  border: 1px solid var(--hub-border);
  border-radius: 18px;
  color: inherit;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.hub-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 30px rgba(7, 12, 22, 0.45);
}

.hub-card :deep(.el-card__body) {
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
}

.detail-pane {
  position: relative;
}

.detail-card {
  background: var(--hub-surface-strong);
  border: 1px solid var(--hub-border);
  border-radius: 20px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
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

.team-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.team-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(10, 16, 28, 0.7);
  border: 1px solid rgba(120, 160, 220, 0.2);
}

.team-name {
  font-weight: 600;
}

.team-meta {
  font-size: 11px;
  color: var(--hub-muted);
}

.detail-empty {
  color: var(--hub-muted);
  font-size: 13px;
}

.auth-dialog :deep(.el-dialog) {
  background: rgba(7, 12, 22, 0.95);
  border: 1px solid rgba(120, 160, 220, 0.2);
  border-radius: 20px;
  box-shadow: 0 24px 60px rgba(7, 12, 22, 0.6);
}

.edit-dialog :deep(.el-dialog) {
  background: rgba(7, 12, 22, 0.95);
  border: 1px solid rgba(120, 160, 220, 0.2);
  border-radius: 20px;
  box-shadow: 0 24px 60px rgba(7, 12, 22, 0.6);
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

@media (max-width: 1180px) {
  .hub-header {
    flex-direction: column;
    align-items: flex-start;
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
}

@media (max-width: 720px) {
  .hub-header {
    padding: 16px 20px;
  }

  .hub-main {
    padding: 24px 20px 0;
  }

  .hub-input {
    width: 100%;
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
