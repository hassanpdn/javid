<script setup>
// «متقاضیان»: everyone looking to buy or rent, with what they want, how many units fit them and whether one of those
// has not been offered yet. «متقاضی جدید از متن» reads a call's notes into a new request.
import { ref, reactive, watch, onMounted, defineAsyncComponent } from "vue"
import { api, fa, estateSession, retryable } from "../lib/api.js"
import { KINDS } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
const ReadDialog = defineAsyncComponent(() => import("./ReadDialog.vue"))

const emit = defineEmits(["open"])
const list = ref(null), adding = ref(false)
const f = reactive({ kind: "", status: "open", mine: false })
const load = async () => {
  list.value = await api("/estate/requests?" + new URLSearchParams({ kind: f.kind, status: f.status, mine: f.mine ? "true" : "false" }))
}
watch(f, () => { list.value = null; load().catch(() => { list.value = [] }) })
onMounted(() => retryable(load))
defineExpose({ reload: load })
const saved = (r) => { adding.value = false; load(); emit("open", r.id) }
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="es-toolbar">
      <div class="tabs" role="tablist" aria-label="نوع">
        <button v-for="(t, k) in { '': 'همه', sale: 'خرید', rent: 'رهن و اجاره' }" :key="k" role="tab" :aria-selected="f.kind === k" :class="{ on: f.kind === k }" @click="f.kind = k">{{ t }}</button>
      </div>
      <select v-model="f.status" class="es-select" aria-label="وضعیت"><option value="open">در جستجو</option><option value="closed">بسته‌شده</option><option value="all">همه</option></select>
      <label v-if="estateSession.user.role === 'agent'" class="es-check"><input v-model="f.mine" type="checkbox">فقط متقاضیان من</label>
      <span class="grow"></span>
      <button class="btn primary" @click="adding = true"><Icon name="plus" :size="18" />متقاضی جدید از متن</button>
    </div>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="6" /></div>
    <div v-else-if="!list.length" class="card empty"><Icon name="users" :size="32" /><p class="muted">متقاضی‌ای با این مشخصات نیست.</p></div>
    <ul v-else class="es-list">
      <li v-for="r in list" :key="r.id">
        <button :class="['card', 'es-row', { closed: r.status !== 'open' }]" @click="emit('open', r.id)">
          <span :class="['tint', r.kind === 'sale' ? 't-primary' : 't-info']"><Icon name="user" :size="20" /></span>
          <span class="es-row-body">
            <span class="es-row-top"><b>{{ r.name }}</b><span class="es-id">{{ r.source_text }}</span></span>
            <span class="es-price">{{ r.kind === 'sale' ? 'خرید' : 'رهن و اجاره' }} · {{ fa(r.budget_text) }}</span>
            <span class="es-meta">{{ r.hoods_list.join('، ') }}<template v-if="r.wants.length"> · {{ fa(r.wants.join('، ')) }}</template></span>
            <span class="es-meta">{{ r.agent }} · ثبت {{ fa(r.created_text) }}<template v-if="r.status !== 'open'"> · {{ r.status_text }}</template></span>
            <span v-if="r.matches" class="es-tags">
              <span class="tag es-t-success"><Icon name="file" :size="12" />{{ fa(r.matches) }} فایل جور</span>
              <span v-if="r.uncalled" class="tag es-t-warning">پیشنهادنشده دارد</span>
            </span>
          </span>
          <Icon name="chevron" :size="18" class="es-go" />
        </button>
      </li>
    </ul>
    <ReadDialog v-if="adding" kind="request" @close="adding = false" @saved="saved" />
  </div>
</template>
