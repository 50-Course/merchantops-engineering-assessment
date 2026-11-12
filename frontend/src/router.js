import { ref } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import CatalogueView from './views/CatalogueView.vue'
import EditorView from './views/EditorView.vue'
import ActivityView from './views/ActivityView.vue'

export const catalogueQuery = ref({})
try {
  catalogueQuery.value = JSON.parse(sessionStorage.getItem('merchantops.catalogue') || '{}')
} catch {
  // Catalogue history remains available in memory if browser storage is unavailable.
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'catalogue', component: CatalogueView },
    { path: '/products/:id(\\d+)', name: 'editor', component: EditorView },
    { path: '/products/:id(\\d+)/activity', name: 'activity', component: ActivityView },
    { path: '/:pathMatch(.*)*', redirect: { name: 'catalogue' } },
  ],
  scrollBehavior(to, from, savedPosition) {
    return savedPosition || (to.path !== from.path ? { top: 0 } : undefined)
  },
})

router.afterEach((to, _from, failure) => {
  if (failure || to.name !== 'catalogue') return
  catalogueQuery.value = to.query
  try {
    sessionStorage.setItem('merchantops.catalogue', JSON.stringify(to.query))
  } catch {
    // Browser storage is optional.
  }
})
