import { computed, onMounted, reactive, ref, watch } from 'vue'
import type { InjectionKey } from 'vue'
import { ElMessageBox } from 'element-plus'
import { createHubClient } from '../client/hubClient'
import { createHubApi } from '../api/hubApi'
import { createHubService } from '../services/hubService'
import type {
  AccessToken,
  AccessTokenCreateRequest,
  AccountProfile,
  AccountUpdateRequest,
  AuthResponse,
  HubTab,
  Organization,
  OrganizationCreateRequest,
  OrganizationInvite,
  OrganizationInviteCreateRequest,
  OrganizationMember,
  OrganizationMemberRequest,
  PackageDetail,
  PackagePermission,
  PackagePermissionCreateRequest,
  PackagePermissionUpdateRequest,
  PackageSummary,
  PageMeta,
  WorkflowDetail,
  WorkflowPermission,
  WorkflowPermissionCreateRequest,
  WorkflowPermissionUpdateRequest,
  WorkflowSummary,
  WorkflowVersionDetail,
  WorkflowVersionSummary
} from '../types/hub'

type HubSelection = { tab: HubTab; id: string }
type LibraryTarget = 'packages' | 'workflows' | 'snapshot'

export function useHubStore() {
  const storageKeys = {
    apiBase: 'hub_api_base',
    token: 'hub_auth_token',
    tokenId: 'hub_auth_token_id'
  }

  const apiBase = ref(localStorage.getItem(storageKeys.apiBase) || 'http://localhost:8310')
  const authToken = ref(localStorage.getItem(storageKeys.token) || '')
  const authTokenId = ref(localStorage.getItem(storageKeys.tokenId) || '')
  const client = createHubClient({
    apiBase,
    authToken,
    storageKeyToken: storageKeys.token
  })
  const api = createHubApi(client)
  const service = createHubService(api)

  const publicLoading = ref(false)
  const publicError = ref('')
  const publicPageSize = 12

  const librarySearchQuery = ref('')
  const libraryTagFilter = ref('')
  const libraryOwnerFilter = ref('')
  const libraryPage = ref(1)
  const libraryPageSize = ref(12)
  const libraryListLoading = ref(false)
  const libraryListError = ref('')
  const libraryPackages = ref<PackageSummary[]>([])
  const libraryWorkflows = ref<WorkflowSummary[]>([])
  const libraryPackageTotal = ref<number | null>(null)
  const libraryWorkflowTotal = ref<number | null>(null)
  const libraryDetailLoading = ref(false)
  const libraryDetailError = ref('')
  const librarySelectedPackage = ref<PackageDetail | null>(null)
  const librarySelectedWorkflow = ref<WorkflowDetail | null>(null)
  const libraryWorkflowVersions = ref<WorkflowVersionSummary[]>([])
  const librarySelectedWorkflowVersion = ref<WorkflowVersionDetail | null>(null)
  const libraryWorkflowVersionLoading = ref(false)
  const libraryWorkflowVersionError = ref('')

  const resolveInitialTab = (): HubTab => {
    if (typeof window === 'undefined') {
      return 'packages'
    }
    const pathMatch = window.location.pathname.match(/\/console\/(packages|workflows|orgs|profile|keys|devices)/)
    if (pathMatch && pathMatch[1]) {
      return pathMatch[1] as HubTab
    }
    const tab = new URLSearchParams(window.location.search).get('tab')
    if (tab === 'account') {
      return 'profile'
    }
    if (tab === 'workflows' || tab === 'orgs' || tab === 'packages' || tab === 'profile' || tab === 'keys') {
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
    if (tab === 'profile' || tab === 'keys' || tab === 'devices') {
      return null
    }
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
  const orgInvites = ref<OrganizationInvite[]>([])
  const orgInvitesLoading = ref(false)
  const orgInvitesError = ref('')
  const orgMembers = ref<OrganizationMember[]>([])
  const orgMembersLoading = ref(false)
  const orgMembersError = ref('')
  const orgOptions = ref<Organization[]>([])
  const orgOptionsLoading = ref(false)
  const orgOptionsError = ref('')

  const selectedPackage = ref<PackageDetail | null>(null)
  const selectedWorkflow = ref<WorkflowDetail | null>(null)
  const selectedOrg = ref<Organization | null>(null)
  const workflowVersions = ref<WorkflowVersionSummary[]>([])
  const selectedWorkflowVersion = ref<WorkflowVersionDetail | null>(null)
  const workflowVersionLoading = ref(false)
  const workflowVersionError = ref('')
  const packagePermissions = ref<PackagePermission[]>([])
  const packagePermissionsLoading = ref(false)
  const packagePermissionsError = ref('')
  const workflowPermissions = ref<WorkflowPermission[]>([])
  const workflowPermissionsLoading = ref(false)
  const workflowPermissionsError = ref('')
  const accountProfile = ref<AccountProfile | null>(null)
  const accountLoading = ref(false)
  const accountError = ref('')
  const accountEditLoading = ref(false)
  const accountEditError = ref('')
  const accountEditForm = reactive<AccountUpdateRequest>({
    displayName: '',
    email: ''
  })
  const accountInvites = ref<OrganizationInvite[]>([])
  const accountInvitesLoading = ref(false)
  const accountInvitesError = ref('')
  const tokens = ref<AccessToken[]>([])
  const tokensLoading = ref(false)
  const tokensError = ref('')
  const tokenCreateLoading = ref(false)
  const tokenCreateError = ref('')
  const tokenCreateResult = ref<AccessToken | null>(null)

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

  const orgInviteOpen = ref(false)
  const orgInviteLoading = ref(false)
  const orgInviteError = ref('')
  const orgInviteForm = reactive<OrganizationInviteCreateRequest>({
    userId: '',
    role: 'member',
    expiresAt: ''
  })

  const hasToken = computed(() => Boolean(authToken.value.trim()))
  const featuredPackages = computed(() => libraryPackages.value.slice(0, 6))
  const featuredWorkflows = computed(() => libraryWorkflows.value.slice(0, 6))
  const topTags = computed(() => {
    const counts = new Map<string, number>()
    const addTag = (tag: string) => {
      const trimmed = tag.trim()
      if (!trimmed) return
      counts.set(trimmed, (counts.get(trimmed) || 0) + 1)
    }
    libraryPackages.value.forEach((pkg) => (pkg.tags || []).forEach(addTag))
    libraryWorkflows.value.forEach((flow) => (flow.tags || []).forEach(addTag))
    return Array.from(counts.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)
  })
  const activeTotal = computed(() => {
    const total =
      activeTab.value === 'packages'
        ? packageTotal.value
        : activeTab.value === 'workflows'
          ? workflowTotal.value
          : activeTab.value === 'orgs'
            ? orgTotal.value
            : 0
    return total ?? 0
  })
  const hasListData = computed(() => {
    if (activeTab.value === 'packages') return packages.value.length > 0
    if (activeTab.value === 'workflows') return workflows.value.length > 0
    if (activeTab.value === 'orgs') return organizations.value.length > 0
    return tokens.value.length > 0
  })
  const packageTotalDisplay = computed(() => (packageTotal.value === null ? '--' : packageTotal.value.toString()))
  const workflowTotalDisplay = computed(() => (workflowTotal.value === null ? '--' : workflowTotal.value.toString()))
  const libraryPackageTotalDisplay = computed(() => (
    libraryPackageTotal.value === null ? '--' : libraryPackageTotal.value.toString()
  ))
  const libraryWorkflowTotalDisplay = computed(() => (
    libraryWorkflowTotal.value === null ? '--' : libraryWorkflowTotal.value.toString()
  ))
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
  const libraryWorkflowPreviewSrc = computed(() => {
    const raw = librarySelectedWorkflowVersion.value?.previewImage || librarySelectedWorkflow.value?.previewImage
    if (!raw) return ''
    return raw.startsWith('data:') ? raw : `data:image/png;base64,${raw}`
  })
  const libraryWorkflowDependencies = computed(
    () => librarySelectedWorkflowVersion.value?.dependencies || []
  )

  const resolvePackageRef = (
    pkg?: { name?: string | null; ownerId?: string | null; ownerName?: string | null } | null,
    fallbackName?: string
  ) => {
    const name = (pkg?.name ?? fallbackName ?? '').trim()
    if (!name) return ''
    if (name.includes('/')) return name
    const owner = (pkg?.ownerId ?? pkg?.ownerName ?? '').trim()
    if (!owner) return name
    return `${owner}/${name}`
  }

  function openAuthDialog() {
    authDialogOpen.value = true
    authError.value = ''
  }

  function selectPublicTag(tag: string) {
    libraryTagFilter.value = libraryTagFilter.value === tag ? '' : tag
    applyLibraryFilters('snapshot')
  }

  function resetAuthForm() {
    authForm.username = ''
    authForm.password = ''
    authForm.displayName = ''
    authForm.email = ''
    authError.value = ''
  }

  function clearAuth() {
    authToken.value = ''
    authTokenId.value = ''
    localStorage.removeItem(storageKeys.token)
    localStorage.removeItem(storageKeys.tokenId)
    searchQuery.value = ''
    tagFilter.value = ''
    ownerFilter.value = ''
    page.value = 1
    packages.value = []
    workflows.value = []
    packageTotal.value = null
    workflowTotal.value = null
    librarySearchQuery.value = ''
    libraryTagFilter.value = ''
    libraryOwnerFilter.value = ''
    libraryPage.value = 1
    libraryPackages.value = []
    libraryWorkflows.value = []
    libraryPackageTotal.value = null
    libraryWorkflowTotal.value = null
    libraryListError.value = ''
    libraryDetailError.value = ''
    clearLibrarySelection()
    organizations.value = []
    orgTotal.value = null
    orgInvites.value = []
    orgInvitesError.value = ''
    orgMembers.value = []
    orgMembersError.value = ''
    orgOptions.value = []
    orgOptionsError.value = ''
    accountProfile.value = null
    accountError.value = ''
    accountEditError.value = ''
    accountEditForm.displayName = ''
    accountEditForm.email = ''
    accountInvites.value = []
    accountInvitesError.value = ''
    tokens.value = []
    tokensError.value = ''
    tokenCreateError.value = ''
    tokenCreateResult.value = null
    orgEditOpen.value = false
    orgEditTarget.value = null
    orgInviteOpen.value = false
    clearSelection()
    void loadLibrarySnapshot()
  }

  function clearSelection() {
    selectedPackage.value = null
    selectedWorkflow.value = null
    selectedOrg.value = null
    workflowVersions.value = []
    selectedWorkflowVersion.value = null
    workflowVersionLoading.value = false
    workflowVersionError.value = ''
    packagePermissions.value = []
    packagePermissionsError.value = ''
    workflowPermissions.value = []
    workflowPermissionsError.value = ''
    orgInvites.value = []
    orgInvitesError.value = ''
    orgMembers.value = []
    orgMembersError.value = ''
  }

  function clearLibrarySelection() {
    librarySelectedPackage.value = null
    librarySelectedWorkflow.value = null
    libraryWorkflowVersions.value = []
    librarySelectedWorkflowVersion.value = null
    libraryWorkflowVersionLoading.value = false
    libraryWorkflowVersionError.value = ''
  }

  function buildQuery(overrides: {
    query?: string
    tag?: string
    owner?: string
    page?: number
    pageSize?: number
  } = {}) {
    const params = new URLSearchParams()
    const query = overrides.query ?? searchQuery.value
    const tag = overrides.tag ?? tagFilter.value
    const owner = overrides.owner ?? ownerFilter.value
    const pageValue = overrides.page ?? page.value
    const pageSizeValue = overrides.pageSize ?? pageSize.value
    if (query) params.set('q', query)
    if (tag) params.set('tag', tag)
    if (owner) params.set('owner', owner)
    params.set('page', String(pageValue))
    params.set('pageSize', String(pageSizeValue))
    return params.toString()
  }

  function buildLibraryQuery(overrides: {
    query?: string
    tag?: string
    owner?: string
    page?: number
    pageSize?: number
  } = {}) {
    const params = new URLSearchParams()
    const query = overrides.query ?? librarySearchQuery.value
    const tag = overrides.tag ?? libraryTagFilter.value
    const owner = overrides.owner ?? libraryOwnerFilter.value
    const pageValue = overrides.page ?? libraryPage.value
    const pageSizeValue = overrides.pageSize ?? libraryPageSize.value
    if (query) params.set('q', query)
    if (tag) params.set('tag', tag)
    if (owner) params.set('owner', owner)
    params.set('page', String(pageValue))
    params.set('pageSize', String(pageSizeValue))
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
      const response = authMode.value === 'login'
        ? await api.login(payload)
        : await api.register(payload)
      const token = response.token?.token?.trim()
      const tokenId = response.token?.id?.trim()
      if (!token) {
        throw new Error('Token missing from response.')
      }
      if (response.account) {
        accountProfile.value = response.account
      }
      authToken.value = token
      authTokenId.value = tokenId || ''
      localStorage.setItem(storageKeys.token, token)
      if (tokenId) {
        localStorage.setItem(storageKeys.tokenId, tokenId)
      } else {
        localStorage.removeItem(storageKeys.tokenId)
      }
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
      const data = await service.fetchPackages(buildQuery())
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
      const data = await service.fetchWorkflows(buildQuery())
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
      const data = await service.fetchOrganizations()
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

  async function loadAccount() {
    accountLoading.value = true
    accountError.value = ''
    try {
      const data = await service.fetchAccount()
      accountProfile.value = data
      accountEditForm.displayName = data.displayName || ''
      accountEditForm.email = data.email || ''
    } catch (error) {
      accountError.value = (error as Error).message
      accountProfile.value = null
      if ((error as Error).message.includes('Unauthorized')) {
        authDialogOpen.value = true
      }
    } finally {
      accountLoading.value = false
    }
  }

  function resetAccountEditForm() {
    accountEditForm.displayName = accountProfile.value?.displayName || ''
    accountEditForm.email = accountProfile.value?.email || ''
    accountEditError.value = ''
  }

  async function updateAccountProfile() {
    if (!accountProfile.value) {
      accountEditError.value = 'Account is not loaded.'
      return
    }
    const displayName = accountEditForm.displayName?.trim()
    const email = accountEditForm.email?.trim()
    if (!displayName && !email) {
      accountEditError.value = 'Provide a display name or email.'
      return
    }
    const payload: AccountUpdateRequest = {}
    if (displayName !== accountProfile.value.displayName) {
      payload.displayName = displayName
    }
    if (email !== accountProfile.value.email) {
      payload.email = email
    }
    if (!Object.keys(payload).length) {
      accountEditError.value = 'No changes to save.'
      return
    }
    accountEditLoading.value = true
    accountEditError.value = ''
    try {
      const updated = await service.updateAccount(payload)
      accountProfile.value = updated
      resetAccountEditForm()
    } catch (error) {
      accountEditError.value = (error as Error).message
    } finally {
      accountEditLoading.value = false
    }
  }

  async function loadTokens() {
    tokensLoading.value = true
    tokensError.value = ''
    try {
      const data = await service.fetchTokens()
      tokens.value = data.items || []
      if (!authTokenId.value && authToken.value) {
        const match = tokens.value.find((token) => token.token && token.token === authToken.value)
        if (match?.id) {
          authTokenId.value = match.id
          localStorage.setItem(storageKeys.tokenId, match.id)
        }
      }
    } catch (error) {
      tokensError.value = (error as Error).message
      tokens.value = []
      if ((error as Error).message.includes('Unauthorized')) {
        authDialogOpen.value = true
      }
    } finally {
      tokensLoading.value = false
    }
  }

  async function loadAccountInvites() {
    accountInvitesLoading.value = true
    accountInvitesError.value = ''
    try {
      const data = await service.fetchAccountInvites()
      accountInvites.value = data.items || []
    } catch (error) {
      accountInvitesError.value = (error as Error).message
      accountInvites.value = []
      if ((error as Error).message.includes('Unauthorized')) {
        authDialogOpen.value = true
      }
    } finally {
      accountInvitesLoading.value = false
    }
  }

  async function loadAccountPanel() {
    await Promise.all([loadAccount(), loadTokens(), loadAccountInvites(), loadOrgOptions()])
  }

  async function loadOrgOptions() {
    orgOptionsLoading.value = true
    orgOptionsError.value = ''
    try {
      const data = await service.fetchOrganizations()
      orgOptions.value = data.items || []
    } catch (error) {
      orgOptionsError.value = (error as Error).message
      orgOptions.value = []
    } finally {
      orgOptionsLoading.value = false
    }
  }

  async function loadOrgInvites(orgId: string) {
    orgInvitesLoading.value = true
    orgInvitesError.value = ''
    try {
      const data = await service.fetchOrganizationInvites(orgId)
      orgInvites.value = data.items || []
    } catch (error) {
      orgInvitesError.value = (error as Error).message
      orgInvites.value = []
    } finally {
      orgInvitesLoading.value = false
    }
  }

  async function loadOrgMembers(orgId: string) {
    orgMembersLoading.value = true
    orgMembersError.value = ''
    try {
      const data = await service.fetchOrganizationMembers(orgId)
      orgMembers.value = data.items || []
    } catch (error) {
      orgMembersError.value = (error as Error).message
      orgMembers.value = []
    } finally {
      orgMembersLoading.value = false
    }
  }

  async function createOrgInvite(orgId: string) {
    orgInviteLoading.value = true
    orgInviteError.value = ''
    try {
      const payload: OrganizationInviteCreateRequest = {
        userId: orgInviteForm.userId.trim(),
        role: orgInviteForm.role,
        expiresAt: orgInviteForm.expiresAt?.trim() || undefined
      }
      if (!payload.userId) {
        throw new Error('User ID is required.')
      }
      await service.createOrganizationInvite(orgId, payload)
      orgInviteForm.userId = ''
      orgInviteForm.role = 'member'
      orgInviteForm.expiresAt = ''
      orgInviteOpen.value = false
      await loadOrgInvites(orgId)
    } catch (error) {
      orgInviteError.value = (error as Error).message
    } finally {
      orgInviteLoading.value = false
    }
  }

  async function revokeOrgInvite(orgId: string, inviteId: string) {
    try {
      await service.revokeOrganizationInvite(orgId, inviteId)
      await loadOrgInvites(orgId)
    } catch (error) {
      orgInvitesError.value = (error as Error).message
    }
  }

  async function acceptOrgInvite(orgId: string, inviteId: string) {
    try {
      await service.acceptOrganizationInvite(orgId, inviteId)
      await Promise.all([loadAccountInvites(), loadOrganizations()])
      if (selectedOrg.value?.id === orgId) {
        await Promise.all([loadOrgInvites(orgId), loadOrgMembers(orgId)])
      }
    } catch (error) {
      accountInvitesError.value = (error as Error).message
    }
  }

  async function declineOrgInvite(orgId: string, inviteId: string) {
    try {
      await service.declineOrganizationInvite(orgId, inviteId)
      await loadAccountInvites()
    } catch (error) {
      accountInvitesError.value = (error as Error).message
    }
  }

  async function updateOrgMemberRole(orgId: string, userId: string, role: OrganizationMemberRequest['role']) {
    try {
      const payload: OrganizationMemberRequest = { userId, role }
      await service.addOrganizationMember(orgId, payload)
      await loadOrgMembers(orgId)
    } catch (error) {
      orgMembersError.value = (error as Error).message
    }
  }

  async function removeOrgMember(orgId: string, userId: string) {
    try {
      await service.removeOrganizationMember(orgId, userId)
      await loadOrgMembers(orgId)
    } catch (error) {
      orgMembersError.value = (error as Error).message
    }
  }

  async function loadWorkflowPermissions(workflowId: string) {
    workflowPermissionsLoading.value = true
    workflowPermissionsError.value = ''
    try {
      const data = await service.fetchWorkflowPermissions(workflowId)
      workflowPermissions.value = data.items || []
    } catch (error) {
      workflowPermissionsError.value = (error as Error).message
      workflowPermissions.value = []
    } finally {
      workflowPermissionsLoading.value = false
    }
  }

  async function loadPackagePermissions(packageName: string) {
    packagePermissionsLoading.value = true
    packagePermissionsError.value = ''
    try {
      const data = await service.fetchPackagePermissions(packageName)
      packagePermissions.value = data.items || []
    } catch (error) {
      packagePermissionsError.value = (error as Error).message
      packagePermissions.value = []
    } finally {
      packagePermissionsLoading.value = false
    }
  }

  async function addWorkflowPermission(
    workflowId: string,
    payload: WorkflowPermissionCreateRequest
  ) {
    workflowPermissionsError.value = ''
    try {
      await service.addWorkflowPermission(workflowId, payload)
      await loadWorkflowPermissions(workflowId)
    } catch (error) {
      workflowPermissionsError.value = (error as Error).message
    }
  }

  async function addPackagePermission(
    packageName: string,
    payload: PackagePermissionCreateRequest
  ) {
    packagePermissionsError.value = ''
    try {
      await service.addPackagePermission(packageName, payload)
      await loadPackagePermissions(packageName)
    } catch (error) {
      packagePermissionsError.value = (error as Error).message
    }
  }

  async function updateWorkflowPermission(
    workflowId: string,
    permissionId: string,
    payload: WorkflowPermissionUpdateRequest
  ) {
    workflowPermissionsError.value = ''
    try {
      await service.updateWorkflowPermission(workflowId, permissionId, payload)
      await loadWorkflowPermissions(workflowId)
    } catch (error) {
      workflowPermissionsError.value = (error as Error).message
    }
  }

  async function updatePackagePermission(
    packageName: string,
    permissionId: string,
    payload: PackagePermissionUpdateRequest
  ) {
    packagePermissionsError.value = ''
    try {
      await service.updatePackagePermission(packageName, permissionId, payload)
      await loadPackagePermissions(packageName)
    } catch (error) {
      packagePermissionsError.value = (error as Error).message
    }
  }

  async function deleteWorkflowPermission(workflowId: string, permissionId: string) {
    workflowPermissionsError.value = ''
    try {
      await service.deleteWorkflowPermission(workflowId, permissionId)
      await loadWorkflowPermissions(workflowId)
    } catch (error) {
      workflowPermissionsError.value = (error as Error).message
    }
  }

  async function deletePackagePermission(packageName: string, permissionId: string) {
    packagePermissionsError.value = ''
    try {
      await service.deletePackagePermission(packageName, permissionId)
      await loadPackagePermissions(packageName)
    } catch (error) {
      packagePermissionsError.value = (error as Error).message
    }
  }

  async function deletePackage(packageName: string) {
    const label = packageName.split('/').pop() || packageName
    try {
      await ElMessageBox.confirm(
        `Delete package "${label}"? This will remove all published versions.`,
        'Confirm delete',
        {
          confirmButtonText: 'Delete package',
          cancelButtonText: 'Cancel',
          type: 'warning',
          customClass: 'hub-message-box'
        }
      )
    } catch {
      return
    }
    detailError.value = ''
    try {
      await service.deletePackage(packageName)
      clearSelection()
      await loadPackages()
    } catch (error) {
      detailError.value = (error as Error).message
    }
  }

  async function loadLibrarySnapshot() {
    publicLoading.value = true
    publicError.value = ''
    clearLibrarySelection()
    const query = buildLibraryQuery({ page: 1, pageSize: publicPageSize })
    try {
      const { packagesData, workflowsData } = await service.fetchPublicSnapshot(query)
      libraryPackages.value = packagesData.items || []
      libraryWorkflows.value = workflowsData.items || []
      libraryPackageTotal.value = packagesData.meta?.total || 0
      libraryWorkflowTotal.value = workflowsData.meta?.total || 0
    } catch (error) {
      publicError.value = (error as Error).message
      libraryPackages.value = []
      libraryWorkflows.value = []
      libraryPackageTotal.value = null
      libraryWorkflowTotal.value = null
    } finally {
      publicLoading.value = false
    }
  }

  async function loadLibraryPackages() {
    libraryListLoading.value = true
    libraryListError.value = ''
    try {
      const data = await service.fetchPackages(buildLibraryQuery())
      libraryPackages.value = data.items || []
      libraryPackageTotal.value = data.meta?.total || 0
    } catch (error) {
      libraryListError.value = (error as Error).message
      libraryPackages.value = []
      libraryPackageTotal.value = null
    } finally {
      libraryListLoading.value = false
    }
  }

  async function loadLibraryWorkflows() {
    libraryListLoading.value = true
    libraryListError.value = ''
    try {
      const data = await service.fetchWorkflows(buildLibraryQuery())
      libraryWorkflows.value = data.items || []
      libraryWorkflowTotal.value = data.meta?.total || 0
    } catch (error) {
      libraryListError.value = (error as Error).message
      libraryWorkflows.value = []
      libraryWorkflowTotal.value = null
    } finally {
      libraryListLoading.value = false
    }
  }

  async function loadLibraryPackageDetail(packageName: string) {
    libraryDetailLoading.value = true
    libraryDetailError.value = ''
    librarySelectedWorkflow.value = null
    libraryWorkflowVersions.value = []
    librarySelectedWorkflowVersion.value = null
    libraryWorkflowVersionLoading.value = false
    libraryWorkflowVersionError.value = ''
    try {
      const detail = await service.fetchPackageDetail(packageName)
      librarySelectedPackage.value = detail
    } catch (error) {
      libraryDetailError.value = (error as Error).message
      librarySelectedPackage.value = null
    } finally {
      libraryDetailLoading.value = false
    }
  }

  async function loadLibraryWorkflowVersionDetail(workflowId: string, versionId?: string) {
    if (!versionId) {
      librarySelectedWorkflowVersion.value = null
      return
    }
    libraryWorkflowVersionLoading.value = true
    libraryWorkflowVersionError.value = ''
    try {
      const detail = await service.fetchWorkflowVersionDetail(workflowId, versionId)
      librarySelectedWorkflowVersion.value = detail
    } catch (error) {
      libraryWorkflowVersionError.value = (error as Error).message
      librarySelectedWorkflowVersion.value = null
    } finally {
      libraryWorkflowVersionLoading.value = false
    }
  }

  async function loadLibraryWorkflowDetails(workflowId: string) {
    libraryDetailLoading.value = true
    libraryDetailError.value = ''
    librarySelectedPackage.value = null
    libraryWorkflowVersions.value = []
    librarySelectedWorkflowVersion.value = null
    libraryWorkflowVersionLoading.value = false
    libraryWorkflowVersionError.value = ''
    try {
      const detail = await service.fetchWorkflowDetail(workflowId)
      const versions = await service.fetchWorkflowVersions(workflowId)
      librarySelectedWorkflow.value = detail
      libraryWorkflowVersions.value = versions.items || []
      if (libraryWorkflowVersions.value.length > 0) {
        void loadLibraryWorkflowVersionDetail(detail.id, libraryWorkflowVersions.value[0].id)
      }
    } catch (error) {
      libraryDetailError.value = (error as Error).message
      librarySelectedWorkflow.value = null
    } finally {
      libraryDetailLoading.value = false
    }
  }

  async function selectLibraryWorkflowVersion(version: WorkflowVersionSummary) {
    if (!librarySelectedWorkflow.value) {
      return
    }
    await loadLibraryWorkflowVersionDetail(librarySelectedWorkflow.value.id, version.id)
  }

  async function selectLibraryPackage(pkg: PackageSummary) {
    await loadLibraryPackageDetail(resolvePackageRef(pkg))
  }

  async function selectLibraryWorkflow(flow: WorkflowSummary) {
    await loadLibraryWorkflowDetails(flow.id)
  }

  function applyLibraryFilters(target: LibraryTarget) {
    libraryPage.value = 1
    if (target === 'packages') {
      void loadLibraryPackages()
      return
    }
    if (target === 'workflows') {
      void loadLibraryWorkflows()
      return
    }
    void loadLibrarySnapshot()
  }

  function resetLibraryFilters(target: LibraryTarget) {
    librarySearchQuery.value = ''
    libraryTagFilter.value = ''
    libraryOwnerFilter.value = ''
    libraryPage.value = 1
    applyLibraryFilters(target)
  }

  function handleLibraryPageSize(target: LibraryTarget) {
    libraryPage.value = 1
    if (target === 'packages') {
      void loadLibraryPackages()
      return
    }
    if (target === 'workflows') {
      void loadLibraryWorkflows()
      return
    }
    void loadLibrarySnapshot()
  }

  async function loadList() {
    clearSelection()
    if (activeTab.value === 'packages') {
      await loadPackages()
      return
    }
    if (activeTab.value === 'workflows') {
      await loadWorkflows()
      return
    }
    if (activeTab.value === 'profile' || activeTab.value === 'keys' || activeTab.value === 'devices') {
      if (!authToken.value) {
        accountError.value = 'Login required to view account.'
        authDialogOpen.value = true
        return
      }
      await loadAccountPanel()
      return
    }
    if (!authToken.value) {
      listError.value = 'Login required to view organizations.'
      authDialogOpen.value = true
      return
    }
    await loadOrganizations()
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
    workflowPermissions.value = []
    workflowPermissionsError.value = ''
    orgInvites.value = []
    orgInvitesError.value = ''
    try {
      const detail = await service.fetchPackageDetail(packageName)
      selectedPackage.value = detail
      if (authToken.value) {
        const ref = resolvePackageRef(detail, packageName)
        void loadPackagePermissions(ref)
      } else {
        packagePermissions.value = []
        packagePermissionsError.value = ''
      }
    } catch (error) {
      detailError.value = (error as Error).message
    } finally {
      detailLoading.value = false
    }
  }

  async function loadWorkflowVersionDetail(workflowId: string, versionId?: string) {
    if (!versionId) {
      selectedWorkflowVersion.value = null
      return
    }
    workflowVersionLoading.value = true
    workflowVersionError.value = ''
    try {
      const detail = await service.fetchWorkflowVersionDetail(workflowId, versionId)
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
    orgInvites.value = []
    orgInvitesError.value = ''
    orgMembers.value = []
    orgMembersError.value = ''
    try {
      const detail = await service.fetchWorkflowDetail(workflowId)
      const versions = await service.fetchWorkflowVersions(workflowId)
      selectedWorkflow.value = detail
      workflowVersions.value = versions.items || []
      if (workflowVersions.value.length > 0) {
        void loadWorkflowVersionDetail(detail.id, workflowVersions.value[0].id)
      }
      void loadWorkflowPermissions(detail.id)
    } catch (error) {
      detailError.value = (error as Error).message
    } finally {
      detailLoading.value = false
    }
  }

  async function selectPackage(pkg: PackageSummary) {
    await loadPackageDetail(resolvePackageRef(pkg))
  }

  async function selectWorkflow(flow: WorkflowSummary) {
    await loadWorkflowDetails(flow.id)
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
    try {
      orgInvites.value = []
      orgInvitesError.value = ''
      orgMembers.value = []
      orgMembersError.value = ''
      await Promise.all([loadOrgInvites(org.id), loadOrgMembers(org.id)])
    } catch {
      // loadOrgInvites handles its own errors
    } finally {
      detailLoading.value = false
    }
  }

  function openOrgCreate() {
    orgEditTarget.value = null
    orgEditForm.name = ''
    orgEditForm.slug = ''
    orgEditError.value = ''
    orgInviteOpen.value = false
    orgEditOpen.value = true
  }

  function openOrgEdit(org: Organization) {
    orgEditTarget.value = org
    orgEditForm.name = org.name
    orgEditForm.slug = org.slug
    orgEditError.value = ''
    orgInviteOpen.value = false
    orgEditOpen.value = true
  }

  async function submitOrgEdit() {
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
    const original = orgEditTarget.value
    if (original && slug !== original.slug) {
      try {
        await ElMessageBox.confirm(
          'Changing the slug will change IDs and invalidate old links. Continue?',
          'Confirm slug change',
          {
            confirmButtonText: 'Change slug',
            cancelButtonText: 'Cancel',
            type: 'warning',
            customClass: 'hub-message-box'
          }
        )
      } catch {
        return
      }
    }
    orgEditLoading.value = true
    orgEditError.value = ''
    try {
      if (!original) {
        const payload: OrganizationCreateRequest = { name, slug }
        const created = await service.createOrganization(payload)
        await loadOrganizations()
        await selectOrganization(created)
        orgEditOpen.value = false
        orgEditTarget.value = null
        return
      }
      const payload: Record<string, string> = {}
      if (name && name !== original.name) payload.name = name
      if (slug && slug !== original.slug) payload.slug = slug
      if (!Object.keys(payload).length) {
        orgEditError.value = 'No changes to save.'
        return
      }
      const updated = await service.updateOrganization(original.id, payload)
      if (selectedOrg.value && selectedOrg.value.id === original.id) {
        selectedOrg.value = updated
        await loadOrgInvites(updated.id)
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

  function openOrgInvite() {
    orgInviteError.value = ''
    orgInviteOpen.value = true
  }

  function clearCreatedToken() {
    tokenCreateResult.value = null
  }

  async function createToken(payload: AccessTokenCreateRequest) {
    tokenCreateError.value = ''
    tokenCreateResult.value = null
    tokenCreateLoading.value = true
    try {
      const result = await service.createToken(payload)
      tokenCreateResult.value = result
      await loadTokens()
    } catch (error) {
      const message = (error as Error).message
      tokenCreateError.value = message
      if (message.includes('Unauthorized')) {
        authDialogOpen.value = true
      }
    } finally {
      tokenCreateLoading.value = false
    }
  }

  async function revokeToken(token: AccessToken) {
    try {
      await ElMessageBox.confirm(
        `Revoke token "${token.label}"?`,
        'Confirm revoke',
        {
          confirmButtonText: 'Revoke token',
          cancelButtonText: 'Cancel',
          type: 'warning',
          customClass: 'hub-message-box'
        }
      )
    } catch {
      return
    }
    tokensError.value = ''
    try {
      await service.revokeToken(token.id)
      await loadTokens()
      if (tokenCreateResult.value?.id === token.id) {
        tokenCreateResult.value = null
      }
    } catch (error) {
      const message = (error as Error).message
      tokensError.value = message
      if (message.includes('Unauthorized')) {
        authDialogOpen.value = true
      }
    }
  }

  function handlePageSize() {
    page.value = 1
    if (hasToken.value) {
      void loadList()
    }
  }

  function applyConsoleFilters() {
    page.value = 1
    if (hasToken.value) {
      void loadList()
    }
  }

  function resetConsoleFilters() {
    searchQuery.value = ''
    tagFilter.value = ''
    ownerFilter.value = ''
    page.value = 1
    if (hasToken.value) {
      void loadList()
    }
  }

  watch(activeTab, () => {
    page.value = 1
    if (hasToken.value) {
      void loadList()
    }
  })

  onMounted(() => {
    if (authToken.value) {
      void loadAccount()
      void loadList()
    } else {
      void loadLibrarySnapshot()
    }
  })

  watch(
    () => authToken.value,
    (value, previous) => {
      if (value && value !== previous) {
        void loadAccount()
      }
      if (!value) {
        accountProfile.value = null
      }
    }
  )

  return {
    apiBase,
    authToken,
    authTokenId,
    publicLoading,
    publicError,
    librarySearchQuery,
    libraryTagFilter,
    libraryOwnerFilter,
    libraryPage,
    libraryPageSize,
    libraryListLoading,
    libraryListError,
    libraryPackages,
    libraryWorkflows,
    libraryPackageTotal,
    libraryWorkflowTotal,
    libraryPackageTotalDisplay,
    libraryWorkflowTotalDisplay,
    libraryDetailLoading,
    libraryDetailError,
    librarySelectedPackage,
    librarySelectedWorkflow,
    libraryWorkflowVersions,
    librarySelectedWorkflowVersion,
    libraryWorkflowVersionLoading,
    libraryWorkflowVersionError,
    activeTab,
    searchQuery,
    tagFilter,
    ownerFilter,
    page,
    pageSize,
    listLoading,
    detailLoading,
    listError,
    detailError,
    packages,
    workflows,
    packageTotal,
    workflowTotal,
    organizations,
    orgTotal,
    orgInvites,
    orgInvitesLoading,
    orgInvitesError,
    orgMembers,
    orgMembersLoading,
    orgMembersError,
    orgOptions,
    orgOptionsLoading,
    orgOptionsError,
    selectedPackage,
    selectedWorkflow,
    selectedOrg,
      workflowVersions,
      selectedWorkflowVersion,
      workflowVersionLoading,
      workflowVersionError,
      packagePermissions,
      packagePermissionsLoading,
      packagePermissionsError,
      workflowPermissions,
      workflowPermissionsLoading,
      workflowPermissionsError,
      accountProfile,
      accountLoading,
      accountError,
      accountEditLoading,
      accountEditError,
      accountEditForm,
      accountInvites,
      accountInvitesLoading,
      accountInvitesError,
    tokens,
    tokensLoading,
    tokensError,
    tokenCreateLoading,
    tokenCreateError,
    tokenCreateResult,
    authDialogOpen,
    authMode,
    authLoading,
    authError,
    authForm,
      orgEditOpen,
      orgEditLoading,
      orgEditError,
      orgEditTarget,
      orgEditForm,
    orgInviteOpen,
    orgInviteLoading,
    orgInviteError,
    orgInviteForm,
    hasToken,
    featuredPackages,
    featuredWorkflows,
    topTags,
    activeTotal,
    hasListData,
    packageTotalDisplay,
    workflowTotalDisplay,
    detailTitle,
    workflowPreviewSrc,
    workflowDependencies,
    libraryWorkflowPreviewSrc,
    libraryWorkflowDependencies,
    resolvePackageRef,
    openAuthDialog,
    selectPublicTag,
      resetAuthForm,
      clearAuth,
      clearSelection,
      clearLibrarySelection,
      resetAccountEditForm,
      updateAccountProfile,
      submitAuth,
      loadLibrarySnapshot,
      loadLibraryPackages,
      loadLibraryWorkflows,
      loadLibraryPackageDetail,
      loadLibraryWorkflowDetails,
      loadList,
      handlePageSize,
      handleLibraryPageSize,
      applyConsoleFilters,
      resetConsoleFilters,
      applyLibraryFilters,
      resetLibraryFilters,
      selectPackage,
      selectWorkflow,
      selectLibraryPackage,
      selectLibraryWorkflow,
      selectOrganization,
      selectWorkflowVersion,
      selectLibraryWorkflowVersion,
      openOrgCreate,
      openOrgEdit,
      submitOrgEdit,
      openOrgInvite,
      createOrgInvite,
      revokeOrgInvite,
      acceptOrgInvite,
      declineOrgInvite,
      loadOrgMembers,
      loadOrgOptions,
      updateOrgMemberRole,
      removeOrgMember,
      loadPackagePermissions,
      addWorkflowPermission,
      updateWorkflowPermission,
      deleteWorkflowPermission,
      addPackagePermission,
      updatePackagePermission,
      deletePackagePermission,
      deletePackage,
      createToken,
      revokeToken,
      clearCreatedToken
  }
}

export type HubStore = ReturnType<typeof useHubStore>
export const hubStoreKey: InjectionKey<HubStore> = Symbol('hubStore')
