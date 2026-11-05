<script setup>
// The teacher's online tests: one button to open a new one for any of their classes, and every test this term with
// how many took it and its average; «نتیجه‌ها» opens the class with the results.
import { ref, onMounted, defineAsyncComponent } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
const ExamDialog = defineAsyncComponent(() => import("./ExamDialog.vue"))
const ResultsDialog = defineAsyncComponent(() => import("./ResultsDialog.vue"))

const emit = defineEmits(["open"])
const d = ref(null), making = ref(null), results = ref(null)
const load = async () => { d.value = await api("/lang/teacher/exams") }
onMounted(() => retryable(load))
const made = () => { making.value = null; load() }
</script>

<template>
  <div class="flex flex-col gap-6">
    <section class="card" data-tour="lg-tests">
      <div class="card-head">آزمون آنلاین جدید</div>
      <p class="muted small" style="margin: 0 0 10px">کلاس را انتخاب کنید. پرسش‌ها از بانک سطح همان کلاس می‌آیند و نمره را خود برنامه می‌دهد؛ زبان‌آموزان آزمون را در پنل خود می‌بینند.</p>
      <Skeleton v-if="!d" kind="chips" />
      <div v-else class="btn-row"><button v-for="c in d.classes" :key="c.id" class="btn" @click="making = c"><Icon name="plus" :size="14" />{{ c.course_name }} · {{ c.pair_text }}</button></div>
    </section>
    <section class="card">
      <div class="card-head">آزمون‌های این ترم</div>
      <Skeleton v-if="!d" kind="row" :count="4" />
      <p v-else-if="!d.exams.length" class="muted small">هنوز آزمونی نیست.</p>
      <div v-else class="flex flex-col gap-3">
        <div v-for="e in d.exams" :key="e.id" :class="['lg-test', 'lg-lv', 'lv-' + e.class.level]">
          <span class="lg-score">{{ fa(e.average ?? "—") }}<small>میانگین</small></span>
          <span class="lg-test-body"><b>{{ fa(e.title) }}</b><small class="muted">{{ e.class.course_name }} · {{ fa(e.taken) }} از {{ fa(e.of) }} نفر · {{ e.open ? 'باز تا ' + fa(e.closes_word) : 'بسته شد ' + fa(e.closes_text) }}</small></span>
          <span v-if="e.open" class="tag k-t-success">باز</span>
          <button class="btn ghost sm" @click="results = e.id">نتیجه‌ها</button>
        </div>
      </div>
    </section>
    <ExamDialog v-if="making" :cls="making" @close="making = null" @saved="made" />
    <ResultsDialog v-if="results" :id="results" @close="results = null" />
  </div>
</template>
