<script setup>
// The teachers: each card with the levels they teach, their hours a week this term and next, their learners, and a
// small week (the three pairs of days by the five slots): green where they come, blue where they teach. A card opens
// the teacher; the manager changes their levels and hours there, or adds a teacher.
import { ref, onMounted, defineAsyncComponent } from "vue"
import { api, fa, retryable, langSession } from "../lib/api.js"
import { instInfo } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
const TeacherDrawer = defineAsyncComponent(() => import("./TeacherDrawer.vue"))

const emit = defineEmits(["open"])
const rows = ref(null), open = ref(null)
const load = async () => { rows.value = await api("/lang/teachers") }
onMounted(() => retryable(load))
const busy = (t, pair, time) => t.classes.current.some((c) => c.pair === pair && c.time === time)
const level = (k) => instInfo.levels.find((l) => l.key === k)
const saved = async () => { await load(); if (open.value?.id) open.value = rows.value.find((t) => t.id === open.value.id) }
</script>

<template>
  <div class="flex flex-col gap-4">
    <div v-if="langSession.user.role === 'owner'" class="k-toolbar"><button class="btn" @click="open = { new: true }"><Icon name="plus" :size="16" />استاد جدید</button>
      <span class="muted small">سبز: ساعت‌هایی که استاد می‌آید · آبی: کلاس این ترم</span></div>
    <Skeleton v-if="!rows" kind="stat" :count="6" />
    <div v-else class="lg-tcards">
      <button v-for="t in rows" :key="t.id" class="card lg-tcard" @click="open = t">
        <div class="lg-tcard-top"><span class="tint t-primary"><Icon name="user" :size="20" /></span>
          <span><b>{{ t.name }}</b><small class="muted">{{ fa(t.hours.current) }} ساعت در هفته · {{ fa(t.learners) }} زبان‌آموز</small></span></div>
        <div class="lg-levels"><span v-for="k in t.levels" :key="k" :class="['lg-chip', 'lg-lv', 'lv-' + k]">{{ level(k)?.fa }}</span></div>
        <div class="lg-avail" aria-hidden="true">
          <template v-for="(name, p) in instInfo.pairs" :key="p"><span>{{ name }}</span>
            <i v-for="s in instInfo.slots" :key="s" :class="{ busy: busy(t, p, s), on: !busy(t, p, s) && (t.avail[p] || []).includes(s) }"></i></template>
        </div>
        <small class="muted">ترم بعد: {{ fa(t.classes.next.length) }} کلاس، {{ fa(t.hours.next) }} ساعت در هفته</small>
      </button>
    </div>
    <TeacherDrawer v-if="open" :teacher="open" @close="open = null" @saved="saved" @open="emit('open', $event)" />
  </div>
</template>
