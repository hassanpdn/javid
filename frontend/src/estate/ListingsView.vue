<script setup>
// «فایل‌ها»: every unit the agency has for sale or rent, filtered by kind, neighbourhood and state («مال من» for an
// agent's own). Each row says what needs doing (no call with the owner, a report due, maybe a duplicate, a match nobody
// called) and opens the listing's drawer. «فایل جدید از متن» reads a pasted ad or note into a new listing.
import { ref, reactive, watch, onMounted, defineAsyncComponent } from "vue"
import { api, fa, estateSession, retryable } from "../lib/api.js"
import { agencyInfo, KINDS } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
const ReadDialog = defineAsyncComponent(() => import("./ReadDialog.vue"))

const emit = defineEmits(["open"])
const props = defineProps({ focus: { type: Number, default: null } })
const list = ref(null), adding = ref(false)
const f = reactive({ kind: "", hood: "", status: "active", mine: false })
const load = async () => {
  const q = new URLSearchParams({ kind: f.kind, hood: f.hood, status: f.status, mine: f.mine ? "true" : "false" })
  list.value = await api("/estate/listings?" + q)
}
watch(f, () => { list.value = null; load().catch(() => { list.value = [] }) })
onMounted(() => retryable(load))
defineExpose({ reload: load })
const saved = (r) => { adding.value = false; load(); emit("open", r.id) }
const TONE = { "بی‌تماس": "warning", "گزارش مالک": "info", "تکراری؟": "info", "تطبیق بی‌تماس": "danger" }
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="es-toolbar" data-tour="el-tools">
      <div class="tabs" role="tablist" aria-label="نوع فایل">
        <button v-for="(t, k) in { '': 'همه', ...KINDS }" :key="k" role="tab" :aria-selected="f.kind === k" :class="{ on: f.kind === k }" @click="f.kind = k">{{ t }}</button>
      </div>
      <select v-model="f.hood" class="es-select" aria-label="محله">
        <option value="">همه‌ی محله‌ها</option>
        <option v-for="h in agencyInfo.agency.hoods" :key="h" :value="h">{{ h }}</option>
      </select>
      <select v-model="f.status" class="es-select" aria-label="وضعیت">
        <option value="active">فعال</option><option value="closed">بسته‌شده</option><option value="all">همه</option>
      </select>
      <label v-if="estateSession.user.role === 'agent'" class="es-check"><input v-model="f.mine" type="checkbox">فقط فایل‌های من</label>
      <span class="grow"></span>
      <button class="btn primary" data-tour="el-new" @click="adding = true"><Icon name="plus" :size="18" />فایل جدید از متن</button>
    </div>

    <div v-if="!list" class="card"><Skeleton kind="row" :count="6" /></div>
    <div v-else-if="!list.length" class="card empty"><Icon name="file" :size="32" /><p class="muted">فایلی با این مشخصات نیست.</p></div>
    <ul v-else class="es-list">
      <li v-for="l in list" :key="l.id">
        <button :class="['card', 'es-row', { closed: l.status !== 'active', focus: focus === l.id }]" @click="emit('open', l.id)">
          <span :class="['tint', l.kind === 'sale' ? 't-primary' : 't-info']"><Icon :name="l.kind === 'sale' ? 'file' : 'refresh'" :size="20" /></span>
          <span class="es-row-body">
            <span class="es-row-top"><b>{{ fa(l.title) }}</b><span class="es-id">فایل {{ fa(l.id) }}</span></span>
            <span class="es-price">{{ fa(l.price_text) }}</span>
            <span class="es-meta">{{ l.kind_text }} · {{ l.street || l.hood }} · {{ fa(l.features.join('، ')) }}</span>
            <span class="es-meta">{{ l.agent }} · {{ l.status === 'active' ? 'تماس با مالک ' + fa(l.contact_text) : l.status_text }}</span>
            <span v-if="l.flags.length || l.matches" class="es-tags">
              <span v-if="l.matches" class="tag es-t-success"><Icon name="users" :size="12" />{{ fa(l.matches) }} متقاضی</span>
              <span v-for="t in l.flags" :key="t" :class="['tag', 'es-t-' + TONE[t]]">{{ t }}</span>
            </span>
          </span>
          <Icon name="chevron" :size="18" class="es-go" />
        </button>
      </li>
    </ul>
    <ReadDialog v-if="adding" kind="listing" @close="adding = false" @saved="saved" />
  </div>
</template>
