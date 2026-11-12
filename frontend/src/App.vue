<script setup>
import { computed, nextTick, provide, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { merchant, signOut } from './api'
import { catalogueQuery } from './router'

const route = useRoute()
const main = ref(null)
let signOutGuard
const signingOut = ref(false)
const signOutError = ref('')
const catalogue = computed(() => ({ name: 'catalogue', query: catalogueQuery.value }))
const initials = merchant.name.trim().split(/\s+/).slice(0, 2).map((word) => word[0]).join('')

provide('merchantops:registerSignOutGuard', (guard) => {
  signOutGuard = guard
})

async function logout() {
  if (signingOut.value || (signOutGuard && !signOutGuard.confirm())) return
  signOutError.value = ''
  signingOut.value = true
  try {
    await signOut()
    signOutGuard?.allowUnload()
    window.location.assign('/login/')
  } catch (error) {
    signOutError.value = error.message
    signingOut.value = false
  }
}

watch(() => route.path, async () => {
  await nextTick()
  main.value?.focus({ preventScroll: true })
})
</script>

<template>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <div class="workspace">
    <aside class="sidebar">
      <RouterLink :to="catalogue" class="brand">
        <span class="brand-mark" aria-hidden="true">M</span>
        MerchantOps
      </RouterLink>

      <nav class="workspace-nav" aria-label="Main navigation">
        <RouterLink :to="catalogue" class="nav-item">
          <span class="catalogue-icon" aria-hidden="true"></span>
          Products
        </RouterLink>
      </nav>

      <div class="account">
        <span class="account-avatar" aria-hidden="true">{{ initials }}</span>
        <div class="account-info">
          <strong>{{ merchant.name }}</strong>
          <button class="text-button" type="button" :disabled="signingOut" @click="logout">
            {{ signingOut ? 'Signing out…' : 'Sign out' }}
          </button>
        </div>
        <p v-if="signOutError" class="account-error" role="alert">{{ signOutError }}</p>
      </div>
    </aside>

    <main id="main-content" ref="main" tabindex="-1" :inert="signingOut">
      <RouterView v-slot="{ Component, route: current }">
        <component :is="Component" :key="current.path" />
      </RouterView>
    </main>
  </div>
</template>
