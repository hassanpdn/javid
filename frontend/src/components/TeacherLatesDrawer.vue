<script setup>
// Manager: every teacher who came late in the last 30 days, with each date and time.
// Those at the warning limit get the same "draft a warning" button as the dashboard alert.
import { ref, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import Icon from "./Icon.vue"
import Avatar from "./Avatar.vue"

defineEmits(["close", "draft"])
const d = ref(null)
onMounted(async () => { d.value = await api("/manager/teachers/lates") })
</script>

<template>
  <div class="overlay" @click.self="$emit('close')">
    <aside class="drawer" v-drawer aria-label="تأخیر معلمان">
      <div class="drawer-head">
        <b class="text-ink">تأخیر معلمان <small class="muted">۳۰ روز اخیر</small></b>
        <button class="icon-btn" @click="$emit('close')" aria-label="بستن"><Icon name="x" /></button>
      </div>
      <div class="drawer-body" tabindex="0">
        <div v-if="!d" class="card"><div class="shimmer"><span></span><span></span><span style="width:60%"></span></div></div>
        <template v-else>
          <p class="muted small">ساعت ورود {{ fa(d.arrival) }} است. با {{ fa(d.limit) }} تأخیر در {{ fa(d.window) }} روز، تذکر کتبی پیشنهاد می‌شود.</p>
          <div v-if="!d.teachers.length" class="card empty-state"><span class="tint lg t-success"><Icon name="check" :size="24" /></span><p>در ۳۰ روز اخیر تأخیری ثبت نشده.</p></div>
          <section v-for="t in d.teachers" :key="t.teacher_id" class="card late-card">
            <div class="head-person">
              <Avatar :name="t.name" :size="40" />
              <div class="grow"><b>{{ t.name }}</b><small class="muted">معلم {{ t.subject }}</small></div>
              <span :class="['tag', t.over_limit ? 'st-hot' : 'st-todo']">{{ fa(t.count) }} تأخیر</span>
            </div>
            <p v-if="t.today" class="small late-today">امروز ساعت {{ fa(t.today) }} رسید.</p>
            <div class="chips">
              <span v-for="l in t.lates" :key="l.date" class="chip">{{ fa(l.date) }} · {{ fa(l.time) }}</span>
            </div>
            <p v-if="t.warning" class="small ok">
              ✓ تذکر کتبی در {{ fa(t.warning.date) }} صادر شد.
              {{ t.warning.acknowledged_at ? 'رؤیت شد: ' + fa(t.warning.acknowledged_at) : 'هنوز رؤیت نشده' }}
            </p>
            <div v-else-if="t.over_limit" class="btn-row">
              <button class="btn sm" @click="$emit('draft', { teacher_id: t.teacher_id, name: t.name })"><Icon name="edit" :size="16" />پیش‌نویس تذکر</button>
            </div>
          </section>
        </template>
      </div>
    </aside>
  </div>
</template>
