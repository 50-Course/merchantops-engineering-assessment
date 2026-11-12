<script setup>
defineProps({
  page: { type: Number, required: true },
  result: { type: Object, required: true },
  label: { type: String, required: true },
  singular: { type: String, required: true },
})
defineEmits(['change'])
</script>

<template>
  <nav class="pagination" :aria-label="label + ' pagination'">
    <span>{{ result.count.toLocaleString() }} {{ result.count === 1 ? singular : label }}</span>
    <div class="pagination-controls">
      <button class="button" type="button" :disabled="!result.previous" @click="$emit('change', page - 1)">
        <span aria-hidden="true">←</span> Previous
      </button>
      <span aria-current="page">Page {{ page }}</span>
      <button class="button" type="button" :disabled="!result.next" @click="$emit('change', page + 1)">
        Next <span aria-hidden="true">→</span>
      </button>
    </div>
  </nav>
</template>
