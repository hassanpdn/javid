<script setup>
// The results of a class's online test, for its teacher and the manager: each learner's mark, who has not taken it,
// how many got each question right (the weak questions first) and each skill's share of right answers.
import { ref, computed, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const props = defineProps({ id: Number })
const emit = defineEmits(["close"])
const d = ref(null)
onMounted(async () => { try { d.value = await api(`/lang/exams/${props.id}/results`) } catch (e) { toast({ tone: "danger", title: e.message }); emit("close") } })
const hardest = computed(() => d.value ? [...d.value.questions].sort((a, b) => a.pct - b.pct) : [])
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog" v-pop role="dialog" aria-label="نتیجه‌ی آزمون" style="max-width: 680px">
      <div class="dialog-head"><h3>{{ d ? fa(d.exam.title) : "نتیجه‌ی آزمون" }}</h3><button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <Skeleton v-if="!d" :lines="6" />
      <template v-else>
        <div class="lg-facts">
          <div><b>{{ fa(d.exam.average ?? "—") }}</b><small>میانگین از ۱۰۰</small></div>
          <div><b>{{ fa(d.exam.taken) }} از {{ fa(d.exam.of) }}</b><small>آزمون داده‌اند</small></div>
          <div><b>{{ d.exam.open ? 'باز' : 'بسته' }}</b><small>{{ d.exam.open ? 'تا ' + fa(d.exam.closes_word) : 'از ' + fa(d.exam.closes_text) }}</small></div>
        </div>
        <div class="lg-skills">
          <div v-for="s in d.skills" :key="s.key" :class="['lg-skill', { weak: s.pct < 60 }]"><span>{{ s.name }}</span><span class="lg-bar"><i :style="{ width: s.pct + '%' }"></i></span><b>{{ fa(s.pct) }}٪</b></div>
        </div>
        <h4 class="text-ink" style="margin: 6px 0 0">پرسش‌ها، سخت‌ترین اول</h4>
        <ul class="k-mini"><li v-for="q in hardest" :key="q.id"><div class="k-row-top"><span class="lg-en" style="text-align: left">{{ q.text }}</span><b>{{ fa(q.right) }}/{{ fa(q.of) }}</b></div>
          <small class="muted">{{ q.skill }} · پاسخ درست: <span class="lg-en">{{ q.answer }}</span></small></li></ul>
        <h4 class="text-ink" style="margin: 6px 0 0">نمره‌ها</h4>
        <ul class="k-mini"><li v-for="r in d.rows" :key="r.name"><div class="k-row-top"><span>{{ r.name }}</span><b :class="{ 'k-late': r.score < 60 }">{{ fa(r.score) }}</b></div><small class="muted">{{ fa(r.at) }}</small></li></ul>
        <p v-if="d.missing.length" class="muted small" style="margin: 0">هنوز نداده‌اند: {{ d.missing.join("، ") }}</p>
      </template>
    </div>
  </div>
</template>
