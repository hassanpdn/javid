<script setup>
// «مهلت‌ها و جلسه‌ها»: every open deadline and hearing, soonest first, in three groups: passed without action, this
// week, later. Each shows the last day (worked out by the server) and opens its case.
import { ref, onMounted } from "vue"
import { api, fa, lawSession, retryable } from "../lib/api.js"
import { toneOf } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open"])
const d = ref(null), mine = ref(lawSession.user.role === "associate")
const load = async () => { d.value = await api("/law/deadlines" + (mine.value ? "?mine=true" : "")) }
onMounted(() => retryable(load))
const GROUPS = [["overdue", "گذشته، بی‌اقدام"], ["week", "هفت روز آینده"], ["later", "بعد از آن"]]
</script>

<template>
  <div class="flex flex-col gap-5">
    <label v-if="lawSession.user.role !== 'secretary'" class="k-check"><input v-model="mine" type="checkbox" @change="load">فقط پرونده‌های من</label>
    <div v-if="!d" class="card"><Skeleton kind="row" :count="6" /></div>
    <template v-else>
      <section v-for="[k, title] in GROUPS" :key="k" class="flex flex-col gap-3">
        <h3 class="k-group">{{ title }} <span class="count">{{ fa(d[k].length) }}</span></h3>
        <p v-if="!d[k].length" class="muted small">موردی نیست.</p>
        <ul class="k-list">
          <li v-for="n in d[k]" :key="n.id">
            <button :class="['card', 'k-row', 'tone-' + toneOf(n.left, n.kind)]" @click="emit('open', n.case_id)">
              <span :class="['k-when', 'tone-' + toneOf(n.left, n.kind)]"><b>{{ fa(n.left_text) }}</b><small>{{ fa(n.deadline ? n.deadline_text : n.hearing_text) }}</small></span>
              <span class="k-row-body">
                <b>{{ n.kind === 'hearing' ? 'جلسه‌ی دادگاه' : n.todo }}</b>
                <span class="k-meta">{{ n.case_title }}</span>
                <span class="k-meta">{{ n.kind_text }}، ابلاغ {{ fa(n.served_text) }} · {{ n.lawyer }}</span>
              </span>
              <Icon name="chevron" :size="18" class="k-go" />
            </button>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
