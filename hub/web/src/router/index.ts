import { createRouter, createWebHistory } from 'vue-router'
import ConsolePage from '../pages/ConsolePage.vue'
import PackageDetailPage from '../pages/PackageDetailPage.vue'
import PackagesPage from '../pages/PackagesPage.vue'
import PublicPage from '../pages/PublicPage.vue'
import WorkflowDetailPage from '../pages/WorkflowDetailPage.vue'
import WorkflowsPage from '../pages/WorkflowsPage.vue'

const routes = [
  { path: '/', name: 'public', component: PublicPage },
  { path: '/packages', name: 'packages', component: PackagesPage },
  { path: '/packages/:owner/:name', name: 'package-detail', component: PackageDetailPage },
  {
    path: '/packages/:name',
    name: 'package-detail-legacy',
    beforeEnter: (to) => {
      const raw = (to.params.name as string || '').trim()
      if (!raw) {
        return { name: 'packages' }
      }
      let decoded = raw
      try {
        decoded = decodeURIComponent(raw)
      } catch {
        decoded = raw
      }
      if (!decoded.includes('/')) {
        return { name: 'packages' }
      }
      const [owner, name] = decoded.split('/', 2)
      return {
        name: 'package-detail',
        params: { owner, name }
      }
    }
  },
  { path: '/workflows', name: 'workflows', component: WorkflowsPage },
  { path: '/workflows/:id', name: 'workflow-detail', component: WorkflowDetailPage },
  { path: '/console', redirect: '/console/packages' },
  { path: '/console/account', redirect: '/console/profile' },
  {
    path: '/console/:section(packages|workflows|orgs|profile|keys|devices)',
    name: 'console',
    component: ConsolePage
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  if (!to.path.startsWith('/console')) {
    return true
  }
  const token = (localStorage.getItem('hub_auth_token') || '').trim()
  if (!token) {
    return { name: 'public' }
  }
  return true
})

export default router
