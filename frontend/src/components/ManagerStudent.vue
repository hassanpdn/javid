<script setup>
// Manager: a short student file. Only progress and attendance; counselor notes and health forms stay with the counselor.
import { ref, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import Icon from "./Icon.vue"
import Avatar from "./Avatar.vue"
import Sparkline from "./Sparkline.vue"
import LevelChip from "./LevelChip.vue"

const props = defineProps(["sid"])
defineEmits(["close"])
const f = ref(null)
onMounted(async () => { f.value = await api(`/manager/students/${props.sid}`) })
</script>

<template>
  <div class="overlay" @click.self="$emit('close')">
    <aside class="drawer" v-drawer :aria-label="f ? 'پرونده ' + f.name : 'پرونده دانش‌آموز'">
      <div class="drawer-head">
        <div class="head-person" v-if="f"><Avatar :name="f.name" :size="46" /><div><b>{{ f.name }}</b><small class="muted">کلاس {{ f.class }} · آموزگار: {{ f.teacher }}</small></div></div>
        <span v-else></span>
        <button class="icon-btn" @click="$emit('close')" aria-label="بستن"><Icon name="x" /></button>
      </div>
      <div class="drawer-body" tabindex="0">
        <div v-if="!f" class="card"><div class="shimmer"><span></span><span></span><span style="width:60%"></span></div></div>
        <template v-else>
          <section class="card">
            <div class="card-head">حضور <small>۳۰ روز اخیر</small></div>
            <div class="grid grid-cols-3 text-center">
              <div><b class="text-ink text-lg">{{ fa(f.attendance.present) }}</b><small class="block muted">روز حاضر</small></div>
              <div><b class="text-danger text-lg">{{ fa(f.attendance.absent) }}</b><small class="block muted">غیبت ({{ fa(f.attendance.unexcused) }} غیرموجه)</small></div>
              <div><b class="text-warning text-lg">{{ fa(f.attendance.late) }}</b><small class="block muted">تأخیر</small></div>
            </div>
            <p v-if="f.attendance.absent_days.length" class="muted small mt-3">
              روزهای غیبت: {{ fa(f.attendance.absent_days.map((d) => d.date + (d.excused ? ' (موجه)' : '')).join('، ')) }}
            </p>
          </section>
          <section class="card">
            <div class="card-head">پیشرفت درسی <small>از مهر تا امروز</small></div>
            <div class="progress-list">
              <div v-for="p in f.progress" :key="p.subject" class="prog-row">
                <span class="prog-sub">{{ p.subject }}</span>
                <Sparkline :points="p.points" :change="p.change" />
                <LevelChip :level="p.now" />
              </div>
              <div class="prog-row prog-axis" aria-hidden="true"><span></span><span class="axis"><span>مهر</span><span>امروز</span></span><span></span></div>
            </div>
            <p v-for="p in f.progress.filter((p) => p.note)" :key="'n' + p.subject" class="teacher-note">یادداشت آموزگار ({{ p.subject }}): {{ p.note }}</p>
          </section>
        </template>
      </div>
    </aside>
  </div>
</template>
