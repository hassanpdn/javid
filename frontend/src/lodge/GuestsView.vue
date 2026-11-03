<script setup>
// «مهمانان»: everyone who booked, with how many stays and whether they have an account on the website.
import { ref, watch, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import Skeleton from "../components/Skeleton.vue"

const list = ref(null), q = ref("")
const load = async () => { list.value = await api("/lodge/guests?q=" + encodeURIComponent(q.value.trim())) }
let timer
watch(q, () => { clearTimeout(timer); timer = setTimeout(() => load().catch(() => {}), 250) })
onMounted(() => retryable(load))
</script>

<template>
  <div class="flex flex-col gap-4">
    <input v-model="q" class="lo-search" placeholder="جستجو: نام یا شماره‌ی همراه" aria-label="جستجو">
    <div v-if="!list" class="card"><Skeleton kind="row" :count="6" /></div>
    <section v-else class="card"><ul class="lo-mini">
      <li v-for="g in list" :key="g.id"><div class="lo-row-top"><b>{{ g.name }}</b><span :class="['tag', g.account ? 'lo-t-success' : 'lo-t-secondary']">{{ g.account ? 'حساب در سایت' : 'بدون حساب' }}</span></div>
        <small class="muted"><span dir="ltr">{{ fa(g.phone) }}</span> · {{ fa(g.stays) }} اقامت<template v-if="g.last"> · آخرین {{ fa(g.last) }}</template></small></li>
    </ul></section>
  </div>
</template>
