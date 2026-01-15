<template>
  <section class="status-panel">
    <div>
      <div class="status-eyebrow">Connection</div>
      <h1>Hub console</h1>
      <p class="status-subtitle">
        Manage packages, workflows, organizations, and access tokens across the hub.
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
</template>

<script setup lang="ts">
defineProps<{
  packageTotalDisplay: string
  workflowTotalDisplay: string
  hasToken: boolean
}>()
</script>
