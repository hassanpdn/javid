<script setup>
// Manager: today's attendance in detail. A student opens a short file (progress and attendance only).
import { ref, computed, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import Icon from "./Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import Avatar from "./Avatar.vue"
import ManagerStudent from "./ManagerStudent.vue"

defineEmits(["close"])
const d = ref(null), sid = ref(null)
const pct = (c) => c.total ? Math.round(100 * c.present / c.total) : 0
const groups = computed(() => d.value ? [
  { key: "absent", title: "غایب", list: d.value.absent, empty: "امروز غایبی نداریم.", recent: "غیبت" },
  { key: "late", title: "تأخیر", list: d.value.late, empty: "امروز کسی دیر نیامده.", recent: "تأخیر" },
] : [])
onMounted(async () => { d.value = await api("/manager/attendance/today") })
</script>

<template>
  <div class="overlay" @click.self="$emit('close')">
    <aside class="drawer" v-drawer aria-label="حضور امروز">
      <div class="drawer-head">
        <b class="text-ink">حضور امروز</b>
        <button class="icon-btn" @click="$emit('close')" aria-label="بستن"><Icon name="x" /></button>
      </div>
      <div class="drawer-body" tabindex="0">
        <template v-if="!d">
          <div class="card"><Skeleton :lines="2" /></div>
          <div class="card"><Skeleton kind="row" round :count="4" /></div>
        </template>
        <template v-else>
          <section class="card">
            <div class="card-head">به تفکیک کلاس</div>
            <ul class="class-list">
              <li v-for="c in d.classes" :key="c.name">
                <span class="grow">کلاس {{ c.name }}</span>
                <span class="muted small">{{ fa(c.present) }} از {{ fa(c.total) }}</span>
                <span class="meter" :class="{ low: pct(c) < 95 }"><span :style="{ width: pct(c) + '%' }"></span></span>
              </li>
            </ul>
          </section>
          <section v-for="g in groups" :key="g.key" class="card list-card">
            <div class="card-head">{{ g.title }} <span v-if="g.list.length" class="count">{{ fa(g.list.length) }}</span></div>
            <p v-if="!g.list.length" class="muted small">{{ g.empty }}</p>
            <button v-for="s in g.list" :key="s.id" class="student-row" @click="sid = s.id">
              <Avatar :name="s.name" :size="36" />
              <span class="sr-main grow">
                <b>{{ s.name }}</b>
                <small class="muted">کلاس {{ s.class }} · {{ fa(s.recent) }} {{ g.recent }} در دو هفته اخیر</small>
              </span>
              <span v-if="g.key === 'absent'" :class="['tag', s.excused ? 'st-done' : 'st-todo']">{{ s.excused ? 'موجه' : 'غیرموجه' }}</span>
              <Icon name="chevron" :size="18" class="chev" />
            </button>
          </section>
        </template>
      </div>
    </aside>
  </div>
  <ManagerStudent v-if="sid" :sid="sid" @close="sid = null" />
</template>
