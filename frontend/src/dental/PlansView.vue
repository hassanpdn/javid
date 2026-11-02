<script setup>
// «طرح‌های درمان»: plans not started (largest first, with days since the last call), plans in progress, finished and
// declined. A plan not started has its follow-up message.
import { ref, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open", "message"])
const d = ref(null), more = ref(false)
onMounted(() => retryable(async () => { d.value = await api("/dental/plans") }))
</script>

<template>
  <div class="flex flex-col gap-5">
    <div v-if="!d" class="card"><Skeleton kind="row" :count="6" /></div>
    <template v-else>
      <section class="flex flex-col gap-3">
        <h3 class="dt-group">شروع‌نشده <span class="count">{{ fa(d.waiting.length) }}</span></h3>
        <p class="muted small">طرح‌هایی که بیمار شنیده و هنوز نوبتی برایشان نگرفته است. اگر {{ fa(d.follow_days) }} روز کسی با بیمار تماس نگرفته باشد، در کارهای امروز هم می‌آید.</p>
        <p v-if="!d.waiting.length" class="muted small">موردی نیست.</p>
        <ul class="dt-list">
          <li v-for="p in d.waiting" :key="p.id" :class="['card', 'dt-row', p.quiet_days >= d.follow_days ? 'tone-warning' : '']" style="cursor: default">
            <span class="tint t-danger"><Icon name="heart" :size="20" /></span>
            <span class="dt-row-body">
              <b>{{ p.title }} · {{ fa(p.total_text) }}</b>
              <span class="dt-meta"><button class="dt-link" @click="emit('open', p.patient_id)">{{ p.patient }}</button> · پیشنهاد {{ fa(p.created_text) }}</span>
              <span :class="['tag', p.quiet_days >= d.follow_days ? 'dt-t-warning' : 'dt-t-secondary']">{{ p.last_contact ? 'آخرین تماس ' + fa(p.quiet_days) + ' روز پیش' : fa(p.quiet_days) + ' روز بدون تماس' }}</span>
              <div class="dt-btns" style="margin-top: 6px"><button class="btn sm" @click="emit('message', { kind: 'followup', plan_id: p.id })"><Icon name="message" :size="14" />پیام پیگیری</button></div>
            </span>
          </li>
        </ul>
      </section>
      <section class="flex flex-col gap-3">
        <h3 class="dt-group">در حال انجام <span class="count">{{ fa(d.going.length) }}</span></h3>
        <ul class="dt-list">
          <li v-for="p in d.going" :key="p.id">
            <button class="card dt-row" @click="emit('open', p.patient_id)">
              <span class="tint t-info"><Icon name="tooth" :size="20" /></span>
              <span class="dt-row-body">
                <b>{{ p.title }} · {{ p.patient }}</b>
                <span class="dt-meta">{{ fa(p.done_count) }} از {{ fa(p.items.length) }} مرحله · {{ fa(p.total_text) }}</span>
                <span class="dt-progress" aria-hidden="true"><i :style="{ width: (100 * p.done_count / p.items.length) + '%' }"></i></span>
                <span v-if="p.next" class="tag dt-t-info">نوبت بعدی: {{ fa(p.next.day_text) }} ساعت {{ fa(p.next.time) }}</span>
                <span v-else class="tag dt-t-warning">نوبتی ندارد</span>
              </span>
              <Icon name="chevron" :size="18" class="dt-go" />
            </button>
          </li>
        </ul>
      </section>
      <button class="btn ghost sm" style="align-self: flex-start" :aria-expanded="more" @click="more = !more">{{ more ? 'بستن' : `تمام‌شده (${fa(d.finished.length)}) و نخواسته (${fa(d.declined.length)})` }}</button>
      <ul v-if="more" class="dt-list">
        <li v-for="p in [...d.finished, ...d.declined]" :key="p.id">
          <button class="card dt-row" @click="emit('open', p.patient_id)">
            <span class="dt-row-body"><b>{{ p.title }} · {{ p.patient }}</b><span class="dt-meta">{{ fa(p.total_text) }} · {{ p.status === 'declined' ? 'بیمار نخواست' : 'تمام شد' }}</span></span>
            <Icon name="chevron" :size="18" class="dt-go" />
          </button>
        </li>
      </ul>
    </template>
  </div>
</template>
