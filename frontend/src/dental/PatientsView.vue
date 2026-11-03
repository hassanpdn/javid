<script setup>
// «بیماران»: search by name or phone; each patient with their next appointment and what they still owe.
import { ref, watch, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open"])
const list = ref(null), q = ref("")
const load = async () => { list.value = await api("/dental/patients?q=" + encodeURIComponent(q.value.trim())) }
let timer
watch(q, () => { clearTimeout(timer); timer = setTimeout(() => load().catch(() => {}), 250) })
onMounted(() => retryable(load))
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="k-toolbar"><input v-model="q" class="k-search" placeholder="جستجو: نام یا شماره‌ی همراه" aria-label="جستجو"></div>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="6" /></div>
    <div v-else-if="!list.length" class="card empty"><Icon name="users" :size="32" /><p class="muted">بیماری با این مشخصات نیست.</p></div>
    <ul v-else class="k-list">
      <li v-for="p in list" :key="p.id">
        <button class="card k-row" @click="emit('open', p.id)">
          <span class="tint t-primary"><Icon name="user" :size="20" /></span>
          <span class="k-row-body">
            <b>{{ p.name }}</b>
            <span class="k-meta"><span dir="ltr">{{ fa(p.phone) }}</span><template v-if="p.last_text"> · آخرین درمان {{ fa(p.last_text) }}</template></span>
            <span v-if="p.next" class="tag k-t-info">نوبت بعدی: {{ fa(p.next.day_text) }} ساعت {{ fa(p.next.time) }}</span>
            <span v-if="p.left > 0" class="tag k-t-danger">مانده: {{ fa(p.left_text) }}</span>
          </span>
          <Icon name="chevron" :size="18" class="k-go" />
        </button>
      </li>
    </ul>
  </div>
</template>
