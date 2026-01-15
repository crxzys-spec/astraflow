<template>
  <section class="workspace library-shell">
    <div class="detail-card">
      <div class="detail-header">
        <div>
          <div class="detail-eyebrow">Package</div>
          <h3>{{ packageTitle }}</h3>
        </div>
        <el-button size="small" plain @click="goBack">Back to packages</el-button>
      </div>

      <el-skeleton v-if="libraryDetailLoading" animated :rows="8" />
      <el-alert
        v-else-if="libraryDetailError"
        type="error"
        show-icon
        :closable="false"
        :title="libraryDetailError"
      />
      <PackageDetail v-else-if="librarySelectedPackage" :pkg="librarySelectedPackage" />
      <div v-else class="detail-empty">
        Package not found.
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PackageDetail from '../components/library/PackageDetail.vue'
import { hubStoreKey, useHubStore } from '../store/hubStore'

const hubStore = inject(hubStoreKey) ?? useHubStore()
const route = useRoute()
const router = useRouter()

const {
  libraryDetailLoading,
  libraryDetailError,
  librarySelectedPackage,
  loadLibraryPackageDetail
} = hubStore

const decodeSegment = (value: string) => {
  const raw = value.trim()
  if (!raw) return ''
  try {
    return decodeURIComponent(raw)
  } catch {
    return raw
  }
}

const packageOwner = computed(() => decodeSegment(route.params.owner as string || ''))
const packageName = computed(() => decodeSegment(route.params.name as string || ''))
const packageRef = computed(() => {
  if (packageOwner.value && packageName.value) {
    return `${packageOwner.value}/${packageName.value}`
  }
  return packageName.value
})
const packageTitle = computed(
  () => librarySelectedPackage.value?.name || packageName.value || 'Package'
)

function goBack() {
  router.push('/packages')
}

function loadDetail() {
  if (!packageRef.value) {
    return
  }
  loadLibraryPackageDetail(packageRef.value)
}

watch(packageRef, () => {
  loadDetail()
})

onMounted(() => {
  loadDetail()
})
</script>
