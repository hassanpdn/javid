<script setup>
// Counselor: students who need attention, with their file in a drawer
import { ref, computed, watch, onMounted, onUnmounted, defineAsyncComponent } from "vue"
import { api, fa, lockScroll } from "../lib/api.js"
import { groupSignals, DOCS_CHAT } from "../lib/constants.js"
import { COUNSELOR } from "../lib/tours.js"
import AppLayout from "../components/AppLayout.vue"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import Avatar from "../components/Avatar.vue"
import CountUp from "../components/CountUp.vue"
// shown only when opened, so their code is downloaded only then
const StudentProfile = defineAsyncComponent(() => import("../components/StudentProfile.vue"))

const list = ref([]), loaded = ref(false), view = ref("flagged"), q = ref(""), openId = ref(null), page = ref("students")
const flagged = computed(() => list.value.filter((s) => s.signals.length))
const shown = computed(() => view.value === "flagged" ? flagged.value
  : list.value.filter((s) => !q.value.trim() || (s.name + s.class).includes(q.value.trim())))
const withSignal = (type) => list.value.filter((s) => s.signals.some((g) => g.type === type)).length
const nav = computed(() => [
  { header: "دانش‌آموزان" },
  { key: "students", label: "دانش‌آموزان", icon: "users", badge: flagged.value.length },
])
const stats = computed(() => [
  { label: "نیاز به توجه", value: flagged.value.length, sub: `از ${fa(list.value.length)} دانش‌آموز`, icon: "alert", tone: "warning" },
  { label: "افت درسی", value: withSignal("grade"), sub: "روند نزولی در یک درس", icon: "trendDown", tone: "danger" },
  { label: "غیبت", value: withSignal("absence"), sub: "غیبت قابل توجه", icon: "calendar", tone: "info" },
  { label: "فرم سلامت", value: withSignal("health"), sub: "نکته در فرم ولی", icon: "heart", tone: "success" },
])
const load = async () => { list.value = await api("/counselor/students"); loaded.value = true }
watch(() => !!openId.value, lockScroll)
onMounted(load)
onUnmounted(() => lockScroll(false))
</script>

<template>
  <AppLayout :chat="DOCS_CHAT" title="پنل مشاور" subtitle="دانش‌آموزانی که این روزها به توجه شما نیاز دارند" :nav="nav" v-model="page" :tour="{ ...COUNSELOR, ready: loaded }">
    <div class="flex flex-col gap-6">
      <div class="grid grid-cols-2 xl:grid-cols-4 gap-6" data-tour="c-stats">
        <div v-for="s in stats" :key="s.label" v-reveal class="card stat" :style="{ '--c': 'var(--' + s.tone + ')' }">
          <div class="stat-top"><span :class="['tint', 't-' + s.tone]"><Icon :name="s.icon" :size="22" /></span><div class="stat-num"><CountUp :value="s.value" /></div></div>
          <div><div class="stat-label">{{ s.label }}</div><div class="stat-sub">{{ s.sub }}</div></div>
        </div>
      </div>

      <section v-reveal class="card p-0 overflow-hidden">
        <div class="toolbar">
          <div class="segmented" data-tour="c-filter">
            <button :class="{ on: view === 'flagged' }" @click="view = 'flagged'">نیاز به توجه <span>{{ fa(flagged.length) }}</span></button>
            <button :class="{ on: view === 'all' }" @click="view = 'all'">همه <span>{{ fa(list.length) }}</span></button>
          </div>
          <input v-if="view === 'all'" class="search small-search" v-model="q" placeholder="جستجوی نام یا کلاس...">
        </div>

        <div v-if="!loaded" class="p-6"><Skeleton kind="row" round :count="6" /></div>
        <div v-else-if="!shown.length" class="empty-state"><span class="tint lg t-success"><Icon name="check" :size="24" /></span><p>موردی نیست.</p></div>
        <div v-else class="student-list">
          <button v-for="s in shown" :key="s.id" v-reveal class="student-row" data-tour="c-student" @click="openId = s.id">
            <Avatar :name="s.name" />
            <span class="sr-main">
              <b>{{ s.name }}</b>
              <small class="muted">کلاس {{ s.class }}</small>
            </span>
            <span class="chips">
              <span v-for="g in groupSignals(s.signals)" :key="g.text" :class="['sig', g.type]">{{ fa(g.text) }}</span>
              <span v-if="s.has_suggestion" class="sig ok">پیام فرستاده شد</span>
            </span>
            <Icon name="chevron" :size="18" class="chev" />
          </button>
        </div>
      </section>
    </div>

    <StudentProfile v-if="openId" :sid="openId" @close="openId = null" @changed="load" />
  </AppLayout>
</template>
