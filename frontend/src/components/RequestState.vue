<script setup>
defineProps({
  loading: Boolean,
  error: { type: String, default: '' },
  label: { type: String, required: true },
})
defineEmits(['retry'])
</script>

<template>
  <div v-if="loading" class="request-state" role="status">
    <span class="spinner" aria-hidden="true"></span> Loading {{ label }}…
  </div>
  <div v-else-if="error" class="request-state">
    <p role="alert">{{ error }}</p>
    <button class="button" type="button" @click="$emit('retry')">Try again</button>
  </div>
</template>
