<script setup>
// «پرونده‌ها»: every open (or closed) case with its client, court and branch, the lawyer on it, and what comes next.
import { ref, reactive, watch, onMounted } from "vue"
import { api, fa, lawSession, retryable } from "../lib/api.js"
import { toneOf } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open"])
const list = ref(null), q = ref("")
const f = reactive({ status: "open", mine: lawSession.user.role === "associate" })
const load = async () => { list.value = await api("/law/cases?" + new URLSearchParams({ status: f.status, mine: f.mine ? "true" : "false" })) }
watch(f, () => { list.value = null; load().catch(() => { list.value = [] }) })
onMounted(() => retryable(load))
const shown = () => (list.value || []).filter((c) => !q.value.trim() || (c.title + c.client + c.number + c.opponent).includes(q.value.trim()))
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="lw-toolbar">
      <input v-model="q" class="lw-search" placeholder="جستجو: نام موکل، موضوع یا شماره‌ی پرونده" aria-label="جستجو">
      <select v-model="f.status" class="lw-select" aria-label="وضعیت"><option value="open">باز</option><option value="closed">مختومه</option><option value="all">همه</option></select>
      <label v-if="lawSession.user.role !== 'secretary'" class="lw-check"><input v-model="f.mine" type="checkbox">فقط پرونده‌های من</label>
    </div>
    <div v-if="!list" class="card"><Skeleton kind="row" :count="6" /></div>
    <div v-else-if="!shown().length" class="card empty"><Icon name="file" :size="32" /><p class="muted">پرونده‌ای با این مشخصات نیست.</p></div>
    <ul v-else class="lw-list">
      <li v-for="c in shown()" :key="c.id">
        <button class="card lw-row" @click="emit('open', c.id)">
          <span class="tint t-primary"><Icon name="file" :size="20" /></span>
          <span class="lw-row-body">
            <b>{{ c.title }}</b>
            <span class="lw-meta">{{ c.field_text }} · {{ c.stage_text }} · {{ c.court }}، شعبه‌ی {{ fa(c.branch) }}</span>
            <span class="lw-meta">طرف دعوا: {{ c.opponent || '-' }} · {{ c.lawyer }}</span>
            <span v-if="c.next" :class="['tag', 'lw-t-' + toneOf(c.next.left, c.next.kind)]">{{ c.next.kind === 'hearing' ? 'جلسه' : c.next.todo }}: {{ fa(c.next.left_text) }}</span>
          </span>
          <Icon name="chevron" :size="18" class="lw-go" />
        </button>
      </li>
    </ul>
  </div>
</template>
