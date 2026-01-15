<template>
  <section class="workspace library-shell">
    <div class="detail-card">
      <div class="detail-header">
        <div>
          <div class="detail-eyebrow">Workflow</div>
          <h3>{{ workflowTitle }}</h3>
        </div>
        <el-button size="small" plain @click="goBack">Back to workflows</el-button>
      </div>

      <el-skeleton v-if="libraryDetailLoading" animated :rows="8" />
      <el-alert
        v-else-if="libraryDetailError"
        type="error"
        show-icon
        :closable="false"
        :title="libraryDetailError"
      />
      <WorkflowDetail
        v-else-if="librarySelectedWorkflow"
        :workflow="librarySelectedWorkflow"
        :previewSrc="libraryWorkflowPreviewSrc"
        :versions="libraryWorkflowVersions"
        :selectedVersion="librarySelectedWorkflowVersion"
        :versionLoading="libraryWorkflowVersionLoading"
        :versionError="libraryWorkflowVersionError"
        :dependencies="libraryWorkflowDependencies"
        @select-version="selectLibraryWorkflowVersion"
      />
      <div v-else class="detail-empty">
        Workflow not found.
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import WorkflowDetail from '../components/library/WorkflowDetail.vue'
import { hubStoreKey, useHubStore } from '../store/hubStore'

const hubStore = inject(hubStoreKey) ?? useHubStore()
const route = useRoute()
const router = useRouter()

const {
  libraryDetailLoading,
  libraryDetailError,
  librarySelectedWorkflow,
  libraryWorkflowVersions,
  librarySelectedWorkflowVersion,
  libraryWorkflowVersionLoading,
  libraryWorkflowVersionError,
  libraryWorkflowPreviewSrc,
  libraryWorkflowDependencies,
  loadLibraryWorkflowDetails,
  selectLibraryWorkflowVersion
} = hubStore

const workflowId = computed(() => {
  const raw = (route.params.id as string || '').trim()
  if (!raw) return ''
  try {
    return decodeURIComponent(raw)
  } catch {
    return raw
  }
})
const workflowTitle = computed(() => librarySelectedWorkflow.value?.name || workflowId.value || 'Workflow')

function goBack() {
  router.push('/workflows')
}

function loadDetail() {
  if (!workflowId.value) {
    return
  }
  loadLibraryWorkflowDetails(workflowId.value)
}

watch(workflowId, () => {
  loadDetail()
})

onMounted(() => {
  loadDetail()
})
</script>
