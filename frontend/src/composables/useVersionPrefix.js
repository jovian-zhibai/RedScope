import { computed } from 'vue'
import { useRoute } from 'vue-router'

export function useVersionPrefix() {
  const route = useRoute()
  const isV2 = computed(() => route.path.startsWith('/v2'))
  const prefix = computed(() => isV2.value ? '/v2' : '')
  const p = (path) => `${prefix.value}${path}`
  return { isV2, prefix, p }
}
