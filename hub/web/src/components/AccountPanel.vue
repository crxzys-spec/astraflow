<template>
  <div
    class="account-layout"
    :class="{
      'account-layout--single': isSingleColumn,
      'account-layout--keys': showKeys,
      'account-layout--sessions': showDevices
    }"
  >
    <template v-if="showKeys">
      <div class="detail-card account-card account-keys-list">
        <el-skeleton v-if="tokensLoading" animated :rows="6" />
        <el-alert
          v-else-if="tokensError"
          type="error"
          show-icon
          :closable="false"
          :title="tokensError"
        />
        <div v-else class="detail-body">
          <div v-if="apiTokens.length === 0" class="detail-empty">
            No API keys yet.
          </div>
          <div v-else class="token-stack token-stack--scroll key-list">
            <button
              v-for="token in apiTokens"
              :key="token.id"
              type="button"
              class="token-row key-row"
              :class="{ 'key-row--active': isSelectedKey(token) }"
              @click="selectKey(token)"
            >
              <div class="token-info">
                <div class="token-label-row">
                  <span class="token-label">{{ token.label }}</span>
                  <span class="token-owner" :class="{ 'token-owner--org': token.orgId }">
                    {{ token.orgId ? resolveOrgName(token.orgId) : 'Personal' }}
                  </span>
                </div>
                <div v-if="token.lastUsedAt" class="token-meta">
                  Last used {{ formatDate(token.lastUsedAt) }}
                </div>
                <div v-else class="token-meta">
                  Created {{ formatDate(token.createdAt) }}
                </div>
                <div class="token-scopes">
                  <el-tag v-for="scope in token.scopes" :key="scope" size="small" type="info">
                    {{ scope }}
                  </el-tag>
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>

      <div class="account-panels">
        <div class="detail-card account-card account-keys-detail">
          <div class="detail-toolbar">
            <el-button size="small" plain @click="toggleCreateKey">
              {{ createOpen ? 'Hide create' : 'New API key' }}
            </el-button>
          </div>
          <el-skeleton v-if="tokensLoading" animated :rows="5" />
          <el-alert
            v-else-if="tokensError"
            type="error"
            show-icon
            :closable="false"
            :title="tokensError"
          />
          <div v-else-if="selectedKey" class="detail-body key-detail">
            <div
              v-if="tokenCreateResult?.token && tokenCreateResult.id === selectedKey.id"
              class="token-result key-inline-secret"
            >
              <div class="token-result-head">
                <div class="token-label">Token secret (shown once)</div>
                <div class="token-head-actions">
                  <el-button size="small" plain @click="copyToken">Copy token</el-button>
                  <el-button size="small" plain @click="clearCreatedToken">Hide</el-button>
                </div>
              </div>
              <div class="token-result-meta">
                Copy and store this token now.
                <span v-if="copyStatus" class="token-copy">{{ copyStatus }}</span>
              </div>
              <pre class="token-secret">{{ tokenCreateResult.token }}</pre>
            </div>
            <div class="key-summary">
              <div class="key-summary-main">
                <div>
                  <div class="key-summary-label">{{ selectedKey.label }}</div>
                  <div class="key-summary-id">
                    Token ID <span>{{ selectedKey.id }}</span>
                  </div>
                </div>
              </div>
              <div class="key-summary-badges">
                <span class="key-badge">Owner {{ selectedKeyOwnerLabel }}</span>
                <span class="key-badge">Created {{ formatDate(selectedKey.createdAt) }}</span>
                <span v-if="selectedKey.lastUsedAt" class="key-badge">
                  Last used {{ formatDate(selectedKey.lastUsedAt) }}
                </span>
                <span v-if="selectedKey.expiresAt" class="key-badge">
                  Expires {{ formatDate(selectedKey.expiresAt) }}
                </span>
              </div>
            </div>
            <div class="key-detail-grid">
              <div class="key-detail-section">
                <div class="section-title">Scopes</div>
                <div class="token-scopes">
                  <el-tag v-for="scope in selectedKey.scopes" :key="scope" size="small" type="info">
                    {{ scope }}
                  </el-tag>
                </div>
              </div>
              <div class="key-detail-section">
                <div class="section-title">Package restriction</div>
                <div class="key-constraint">
                  {{ selectedKey.packageName || 'All packages' }}
                </div>
              </div>
              <div class="key-detail-section">
                <div class="section-title">Owner</div>
                <div class="key-constraint">
                  {{ selectedKeyOwnerLabel }}
                </div>
              </div>
            </div>
            <div class="detail-section key-actions">
              <div class="section-title">Actions</div>
              <el-button size="small" plain @click="revokeToken(selectedKey)">Revoke key</el-button>
            </div>
          </div>
          <div v-else class="detail-empty">
            Select an API key to see details.
          </div>
        </div>

      </div>
    </template>

    <template v-else>
      <template v-if="showProfile">
        <div class="account-panels">
          <div class="detail-card account-card">
            <el-skeleton v-if="accountLoading" animated :rows="4" />
            <el-alert
              v-else-if="accountError"
              type="error"
              show-icon
              :closable="false"
              :title="accountError"
            />
            <div v-else-if="account" class="detail-body">
              <el-form label-position="top" class="account-form">
                <el-form-item label="Username">
                  <el-input :model-value="account.username" disabled />
                </el-form-item>
                <el-form-item label="Display name">
                  <el-input v-model="accountEditForm.displayName" placeholder="Add a display name" />
                </el-form-item>
                <el-form-item label="Email">
                  <el-input v-model="accountEditForm.email" placeholder="name@example.com" />
                </el-form-item>
                <el-form-item label="Account ID">
                  <el-input :model-value="account.id" disabled />
                </el-form-item>
              </el-form>
              <div v-if="accountEditError" class="form-hint form-hint--error">
                {{ accountEditError }}
              </div>
              <div class="account-actions">
                <el-button plain @click="resetAccountEdit">Reset</el-button>
                <el-button type="primary" :loading="accountEditLoading" @click="submitAccountEdit">
                  Save changes
                </el-button>
              </div>
            </div>
            <div v-else class="detail-empty">
              No account loaded.
            </div>
          </div>

          <div class="detail-card account-card account-invites">
            <div class="detail-header">
              <div>
                <div class="detail-eyebrow">Invites</div>
                <h3>Pending invitations</h3>
              </div>
            </div>
            <el-skeleton v-if="accountInvitesLoading" animated :rows="4" />
            <el-alert
              v-else-if="accountInvitesError"
              type="error"
              show-icon
              :closable="false"
              :title="accountInvitesError"
            />
            <div v-else class="detail-body">
              <div v-if="pendingInvites.length === 0" class="detail-empty">
                No pending invitations.
              </div>
              <div v-else class="detail-list">
                <div v-for="invite in pendingInvites" :key="invite.id" class="detail-row">
                  <div class="detail-row__main">
                    <div class="detail-row__title">{{ resolveOrgName(invite.orgId) }}</div>
                    <div class="detail-row__meta">
                      Role {{ invite.role }} - Invited by {{ invite.invitedBy }}
                    </div>
                  </div>
                  <div class="detail-row__actions">
                    <el-button size="small" type="primary" @click="acceptInvite(invite)">
                      Accept
                    </el-button>
                    <el-button size="small" plain @click="declineInvite(invite)">
                      Decline
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="detail-card account-card account-sessions-list">
          <el-skeleton v-if="tokensLoading" animated :rows="6" />
          <el-alert
            v-else-if="tokensError"
            type="error"
            show-icon
            :closable="false"
            :title="tokensError"
          />
          <div v-else class="detail-body">
            <div v-if="loginTokensSorted.length === 0" class="detail-empty">
              No active sessions.
            </div>
            <div v-else class="token-stack token-stack--scroll session-list">
              <button
                v-for="token in loginTokensSorted"
                :key="token.id"
                type="button"
                class="token-row session-row"
                :class="{
                  'session-row--active': isSelectedSession(token),
                  'token-row--current': isCurrentToken(token)
                }"
                @click="selectSession(token)"
              >
                <div class="token-info">
                  <div class="session-row__header">
                    <span class="session-row__title">{{ formatSessionLabel(token) }}</span>
                    <span
                      class="session-chip"
                      :class="{ 'session-chip--current': isCurrentToken(token) }"
                    >
                      {{ isCurrentToken(token) ? 'Current' : 'Active' }}
                    </span>
                  </div>
                  <div class="session-row__meta">
                    <div class="session-row__meta-item">
                      <span class="session-row__meta-label">
                        {{ token.lastUsedAt ? 'Last used' : 'Created' }}
                      </span>
                      <span class="session-row__meta-value">
                        {{ token.lastUsedAt ? formatDate(token.lastUsedAt) : formatDate(token.createdAt) }}
                      </span>
                    </div>
                    <div class="session-row__meta-item">
                      <span class="session-row__meta-label">IP</span>
                      <span class="session-row__meta-value">
                        {{ token.lastUsedIp || token.createdIp || 'Unknown' }}
                      </span>
                    </div>
                  </div>
                  <div class="session-row__id">ID {{ shortId(token.id) }}</div>
                </div>
              </button>
            </div>
          </div>
        </div>

        <div class="detail-card account-card account-sessions-detail">
          <el-skeleton v-if="tokensLoading" animated :rows="5" />
          <el-alert
            v-else-if="tokensError"
            type="error"
            show-icon
            :closable="false"
            :title="tokensError"
          />
          <div v-else-if="selectedSession" class="detail-body">
            <div class="session-detail-header">
              <div class="session-detail-title">
                <div class="section-title">Session details</div>
                <div class="session-detail-name">{{ formatSessionLabel(selectedSession) }}</div>
              </div>
              <div class="session-detail-status">
                <span
                  class="session-chip"
                  :class="{ 'session-chip--current': isCurrentToken(selectedSession) }"
                >
                  {{ isCurrentToken(selectedSession) ? 'Current session' : 'Active session' }}
                </span>
              </div>
            </div>
            <div class="session-kpis">
              <div class="session-kpi">
                <span class="session-kpi__label">Last used</span>
                <span class="session-kpi__value">
                  {{ selectedSession.lastUsedAt ? formatDate(selectedSession.lastUsedAt) : 'Never' }}
                </span>
              </div>
              <div class="session-kpi">
                <span class="session-kpi__label">IP</span>
                <span class="session-kpi__value">
                  {{ selectedSession.lastUsedIp || selectedSession.createdIp || 'Unknown' }}
                </span>
              </div>
              <div class="session-kpi">
                <span class="session-kpi__label">Expires</span>
                <span
                  class="session-kpi__value"
                  :class="{ 'session-kpi__value--muted': !selectedSession.expiresAt }"
                >
                  {{ selectedSession.expiresAt ? formatDate(selectedSession.expiresAt) : 'No expiry' }}
                </span>
              </div>
            </div>
            <div class="session-detail-grid">
              <div class="session-detail-main">
                <div class="detail-section session-section">
                  <div class="section-title">Identity</div>
                  <div class="detail-meta session-meta-grid">
                  <div>
                    <span class="meta-label">Label</span>
                    <span>{{ selectedSession.label || 'session' }}</span>
                  </div>
                  <div>
                    <span class="meta-label">Session ID</span>
                    <span>{{ selectedSession.id }}</span>
                  </div>
                  <div>
                    <span class="meta-label">Created</span>
                    <span>{{ formatDate(selectedSession.createdAt) }}</span>
                  </div>
                  <div v-if="selectedSession.createdIp">
                    <span class="meta-label">Created IP</span>
                    <span>{{ selectedSession.createdIp }}</span>
                  </div>
                  </div>
                </div>
              </div>
              <div class="session-detail-aside">
                <div class="detail-section session-section">
                  <div class="section-title">Agent</div>
                  <div class="session-agent">
                    <div class="session-agent-item">
                      <span class="meta-label">Created agent</span>
                      <span>{{ formatAgent(selectedSession.createdUserAgent) }}</span>
                    </div>
                    <div class="session-agent-item">
                      <span class="meta-label">Last agent</span>
                      <span>{{ formatAgent(selectedSession.lastUsedUserAgent) }}</span>
                    </div>
                  </div>
                </div>
                <div class="detail-section session-section session-actions">
                  <div class="section-title">Actions</div>
                  <el-button
                    size="small"
                    plain
                    :disabled="isCurrentToken(selectedSession)"
                    @click="revokeToken(selectedSession)"
                  >
                    Sign out
                  </el-button>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="detail-empty">
            Select a session to see details.
          </div>
        </div>
      </template>
    </template>
  </div>

  <el-dialog
    v-model="createOpen"
    width="520px"
    class="create-key-dialog"
    :show-close="false"
  >
    <template #header>
      <div class="detail-header">
        <div>
          <div class="detail-eyebrow">Access</div>
          <h3>Create API key</h3>
        </div>
        <el-button size="small" plain @click="createOpen = false">Close</el-button>
      </div>
    </template>

    <div class="key-dialog-body">
      <div class="key-callout">
        <div class="key-callout-title">One-time secret</div>
        <div class="key-callout-text">
          Create API keys for API automation. Publishing happens through the API/CLI. Tokens are shown once.
        </div>
      </div>

      <div v-if="tokenCreateResult?.token" class="token-result key-result-panel">
        <div class="token-result-head">
          <div class="token-label">Token created</div>
          <div class="token-head-actions">
            <el-button size="small" plain @click="copyToken">Copy token</el-button>
            <el-button size="small" plain @click="clearCreatedToken">Hide</el-button>
          </div>
        </div>
        <div class="token-result-meta">
          Copy and store this token now. It will not be shown again.
          <span v-if="copyStatus" class="token-copy">{{ copyStatus }}</span>
        </div>
        <pre class="token-secret">{{ tokenCreateResult.token }}</pre>
      </div>

      <el-form label-position="top" class="token-form key-form-panel">
        <div class="key-form-section">
          <div class="key-form-title">Identity</div>
          <el-form-item label="Label">
            <el-input v-model="tokenForm.label" placeholder="e.g. workstation api" />
          </el-form-item>
          <el-form-item label="Owner">
            <el-select
              v-model="tokenForm.orgId"
              clearable
              placeholder="Personal account"
              :loading="orgOptionsLoading"
            >
              <el-option label="Personal account" value="" />
              <el-option
                v-for="org in orgOptions"
                :key="org.id"
                :label="org.name"
                :value="org.id"
              />
            </el-select>
          </el-form-item>
          <div v-if="orgOptionsError" class="form-hint form-hint--error">
            {{ orgOptionsError }}
          </div>
        </div>
        <div class="key-form-section">
          <div class="key-form-title">Permissions</div>
          <el-form-item label="Scopes">
            <el-checkbox-group v-model="tokenForm.scopes" class="key-scope-group">
              <el-checkbox value="read">Read</el-checkbox>
              <el-checkbox value="publish">Publish (API)</el-checkbox>
              <el-checkbox value="admin">Admin</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
        </div>
        <div class="key-form-section">
          <div class="key-form-title">Constraints</div>
          <el-form-item label="Package restriction (optional)">
            <el-input v-model="tokenForm.packageName" placeholder="package.name.optional" />
          </el-form-item>
          <el-form-item label="Expires at (optional)">
            <el-input v-model="tokenForm.expiresAt" placeholder="2026-12-31T00:00:00Z" />
          </el-form-item>
        </div>
      </el-form>

      <el-alert
        v-if="formError"
        type="error"
        show-icon
        :closable="false"
        :title="formError"
      />
      <el-alert
        v-if="tokenCreateError"
        type="error"
        show-icon
        :closable="false"
        :title="tokenCreateError"
      />

      <div class="token-actions key-form-actions">
        <el-button plain @click="resetTokenForm">Reset</el-button>
        <el-button type="primary" :loading="tokenCreateLoading" @click="submitToken">
          Create token
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type {
  AccessToken,
  AccessTokenCreateRequest,
  AccountProfile,
  AccountUpdateRequest,
  Organization,
  OrganizationInvite,
  TokenScope
} from '../types/hub'

const props = defineProps<{
  account: AccountProfile | null
  accountLoading: boolean
  accountError: string
  accountInvites: OrganizationInvite[]
  accountInvitesLoading: boolean
  accountInvitesError: string
  accountEditForm: AccountUpdateRequest
  accountEditLoading: boolean
  accountEditError: string
  tokens: AccessToken[]
  tokensLoading: boolean
  tokensError: string
  tokenCreateLoading: boolean
  tokenCreateError: string
  tokenCreateResult: AccessToken | null
  currentTokenId?: string
  orgOptions: Organization[]
  orgOptionsLoading: boolean
  orgOptionsError: string
  mode?: 'profile' | 'keys' | 'devices'
}>()

const emit = defineEmits<{
  (e: 'create-token', payload: AccessTokenCreateRequest): void
  (e: 'revoke-token', token: AccessToken): void
  (e: 'clear-created-token'): void
  (e: 'accept-org-invite', invite: OrganizationInvite): void
  (e: 'decline-org-invite', invite: OrganizationInvite): void
  (e: 'update-account'): void
  (e: 'reset-account-edit'): void
}>()

const tokenForm = reactive<{
  label: string
  scopes: TokenScope[]
  packageName: string
  orgId: string
  expiresAt: string
}>({
  label: '',
  scopes: ['publish'],
  packageName: '',
  orgId: '',
  expiresAt: ''
})

const formError = ref('')
const copyStatus = ref('')
const modeValue = computed(() => props.mode || 'profile')
const currentTokenIdValue = computed(() => (props.currentTokenId || '').trim())
const apiTokens = computed(() => props.tokens.filter((token) => !isLoginToken(token)))
const loginTokens = computed(() => props.tokens.filter((token) => isLoginToken(token)))
const pendingInvites = computed(() =>
  props.accountInvites.filter((invite) => invite.status === 'pending')
)
const orgNameMap = computed(() => {
  const map = new Map<string, string>()
  props.orgOptions.forEach((org) => {
    map.set(org.id, org.name)
  })
  return map
})
const showProfile = computed(() => modeValue.value === 'profile')
const showKeys = computed(() => modeValue.value === 'keys')
const showDevices = computed(() => modeValue.value === 'devices')
const isSingleColumn = computed(() => modeValue.value === 'profile')
const selectedKeyId = ref('')
const selectedKey = computed(() => apiTokens.value.find((token) => token.id === selectedKeyId.value) || null)
const selectedKeyOwnerLabel = computed(() => {
  if (!selectedKey.value) return 'Personal'
  return tokenOwnerLabel(selectedKey.value)
})
const createOpen = ref(false)
const loginTokensSorted = computed(() => {
  const tokens = [...loginTokens.value]
  tokens.sort((a, b) => {
    const currentA = isCurrentToken(a)
    const currentB = isCurrentToken(b)
    if (currentA !== currentB) return currentA ? -1 : 1
    const lastA = a.lastUsedAt ? new Date(a.lastUsedAt).getTime() : 0
    const lastB = b.lastUsedAt ? new Date(b.lastUsedAt).getTime() : 0
    if (lastA !== lastB) return lastB - lastA
    const createdA = a.createdAt ? new Date(a.createdAt).getTime() : 0
    const createdB = b.createdAt ? new Date(b.createdAt).getTime() : 0
    return createdB - createdA
  })
  return tokens
})
const selectedSessionId = ref('')
const selectedSession = computed(
  () => loginTokensSorted.value.find((token) => token.id === selectedSessionId.value) || null
)

function isLoginToken(token: AccessToken) {
  const label = (token.label || '').trim().toLowerCase()
  return label === 'login' || label === 'register'
}

function resolveOrgName(orgId?: string) {
  if (!orgId) return ''
  return orgNameMap.value.get(orgId) || orgId
}

function tokenOwnerLabel(token: AccessToken) {
  if (token.orgId) {
    return resolveOrgName(token.orgId)
  }
  return 'Personal'
}

function acceptInvite(invite: OrganizationInvite) {
  emit('accept-org-invite', invite)
}

function declineInvite(invite: OrganizationInvite) {
  emit('decline-org-invite', invite)
}

function submitAccountEdit() {
  emit('update-account')
}

function resetAccountEdit() {
  emit('reset-account-edit')
}

function selectKey(token: AccessToken) {
  selectedKeyId.value = token.id
}

function isSelectedKey(token: AccessToken) {
  return token.id === selectedKeyId.value
}

function selectSession(token: AccessToken) {
  selectedSessionId.value = token.id
}

function isSelectedSession(token: AccessToken) {
  return token.id === selectedSessionId.value
}

function toggleCreateKey() {
  createOpen.value = !createOpen.value
}

function isCurrentToken(token: AccessToken) {
  const current = currentTokenIdValue.value
  return Boolean(current && token.id && token.id === current)
}

function resetTokenForm() {
  tokenForm.label = ''
  tokenForm.scopes = ['publish']
  tokenForm.packageName = ''
  tokenForm.orgId = ''
  tokenForm.expiresAt = ''
  formError.value = ''
}

function submitToken() {
  formError.value = ''
  copyStatus.value = ''
  const label = tokenForm.label.trim()
  if (!label) {
    formError.value = 'Label is required.'
    return
  }
  if (!tokenForm.scopes.length) {
    formError.value = 'Select at least one scope.'
    return
  }
  const payload: AccessTokenCreateRequest = {
    label,
    scopes: [...tokenForm.scopes]
  }
  const packageName = tokenForm.packageName.trim()
  const orgId = tokenForm.orgId.trim()
  const expiresAt = tokenForm.expiresAt.trim()
  if (packageName) payload.packageName = packageName
  if (orgId) payload.orgId = orgId
  if (expiresAt) payload.expiresAt = expiresAt
  emit('create-token', payload)
}

function revokeToken(token: AccessToken) {
  emit('revoke-token', token)
}

function clearCreatedToken() {
  emit('clear-created-token')
}

function copyToken() {
  const token = props.tokenCreateResult?.token
  if (!token) return
  if (!navigator.clipboard) {
    copyStatus.value = 'Clipboard not available'
    return
  }
  navigator.clipboard.writeText(token).then(
    () => {
      copyStatus.value = 'Copied'
    },
    () => {
      copyStatus.value = 'Copy failed'
    }
  )
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

function formatAgent(value?: string) {
  if (!value) return 'Unknown'
  const trimmed = value.trim()
  if (!trimmed) return 'Unknown'
  if (trimmed.length <= 90) return trimmed
  return `${trimmed.slice(0, 90)}...`
}

function shortId(value?: string) {
  if (!value) return 'Unknown'
  if (value.length <= 12) return value
  return `${value.slice(0, 6)}...${value.slice(-4)}`
}

function formatSessionLabel(token: AccessToken) {
  const label = (token.label || '').trim()
  if (!label) return 'Session'
  const lower = label.toLowerCase()
  if (lower === 'login' || lower === 'register') return 'Web session'
  return label
}

watch(
  () => props.tokenCreateResult?.token,
  (value) => {
    if (value) {
      resetTokenForm()
      copyStatus.value = ''
      createOpen.value = true
      return
    }
    copyStatus.value = ''
  }
)

watch(
  () => apiTokens.value,
  (tokens) => {
    if (!tokens.length) {
      selectedKeyId.value = ''
      return
    }
    if (!selectedKeyId.value || !tokens.some((token) => token.id === selectedKeyId.value)) {
      selectedKeyId.value = tokens[0].id
    }
  },
  { immediate: true }
)

watch(
  () => loginTokensSorted.value,
  (tokens) => {
    if (!tokens.length) {
      selectedSessionId.value = ''
      return
    }
    if (
      !selectedSessionId.value
      || !tokens.some((token) => token.id === selectedSessionId.value)
    ) {
      const current = tokens.find((token) => isCurrentToken(token))
      selectedSessionId.value = current?.id || tokens[0].id
    }
  },
  { immediate: true }
)

watch(
  () => props.tokenCreateResult?.id,
  (value) => {
    if (value && showKeys.value) {
      selectedKeyId.value = value
    }
  }
)
</script>
