import { onScopeDispose, ref, shallowRef } from 'vue'

export function useResource() {
  const data = shallowRef(null)
  const loading = ref(false)
  const error = ref('')
  let active

  async function load(read) {
    active?.abort()
    const request = new AbortController()
    active = request
    data.value = null
    error.value = ''
    loading.value = true
    try {
      const result = await read(request.signal)
      if (!request.signal.aborted) data.value = result
    } catch (failure) {
      if (!request.signal.aborted) error.value = failure.message
    } finally {
      if (!request.signal.aborted) loading.value = false
    }
  }

  onScopeDispose(() => active?.abort())
  return { data, loading, error, load }
}

export function pageNumber(value) {
  const page = typeof value === 'string' ? Number(value) : 1
  return Number.isSafeInteger(page) && page >= 1 ? page : 1
}
