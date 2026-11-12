<script setup>
import { computed, ref, watch } from 'vue'
import { productImagePattern } from '../api'

const props = defineProps({
  src: String,
  alt: { type: String, default: '' },
})
const localImage = new RegExp('^' + productImagePattern + '$')
const source = computed(() => localImage.test(props.src || '') ? props.src : '')
const failed = ref(false)

watch(source, () => { failed.value = false })

function onError(event) {
  if (event.currentTarget.getAttribute('src') === source.value) failed.value = true
}
</script>

<template>
  <span class="product-thumbnail">
    <img v-if="source && !failed" :key="source" :src="source" :alt="alt" decoding="async" @error="onError" />
    <span v-else class="package-icon" aria-hidden="true"></span>
  </span>
</template>
