import { createRouter, createWebHistory } from 'vue-router'

import Overview from '@/views/Overview.vue'
import WorkbenchView from '@/views/WorkbenchView.vue'
import BoothPipelineView from '@/views/BoothPipelineView.vue'
import QuotaDashboardView from '@/views/QuotaDashboardView.vue'
import EmergencyPanelView from '@/views/EmergencyPanelView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'overview', component: Overview },
    { path: '/pipeline', name: 'pipeline', component: BoothPipelineView },
    { path: '/dashboard', name: 'dashboard', component: QuotaDashboardView },
    // 固定路径要放在 /:moduleKey 之前，否则会被动态模块路由抢先匹配
    { path: '/emergency', name: 'emergency', component: EmergencyPanelView },
    { path: '/:moduleKey', name: 'module', component: WorkbenchView, props: true },
  ],
})

export default router
