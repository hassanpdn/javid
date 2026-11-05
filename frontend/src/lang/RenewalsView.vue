<script setup>
// Next term's registration, for the secretary: every learner of this term not yet registered for the next one, with
// the class they would go on to (their teacher's, when there is one). «پیام» drafts the reminder; «ثبت‌نام» puts them in
// that class at once.
import { ref, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open", "message", "changed"])
const d = ref(null), busy = ref(0)
const load = async () => { d.value = await api("/lang/renewals") }
onMounted(() => retryable(load))
async function enrol(r) {
  busy.value = r.student_id
  try { await api("/lang/enroll", { student_id: r.student_id, class_id: r.class.id }); toast({ tone: "success", title: "ثبت‌نام شد", body: `${r.name}، ${r.next}` }); await load(); emit("changed") }
  catch (e) { toast({ tone: "danger", title: e.message }) } finally { busy.value = 0 }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <p v-if="d" class="lg-next" data-tour="lg-renew"><Icon name="calendar" :size="20" /><span>{{ fa(d.term.name) }} {{ fa(d.term.days_left) }} روز دیگر تمام می‌شود و {{ fa(d.next_term.name) }} از {{ fa(d.next_term.start_long) }} شروع می‌شود. <b>{{ fa(d.rows.length) }} نفر</b> هنوز ثبت‌نام نکرده‌اند.</span></p>
    <Skeleton v-if="!d" kind="row" :count="8" />
    <ul v-else class="k-list">
      <li v-for="r in d.rows" :key="r.student_id" class="card k-row" style="cursor: default; flex-wrap: wrap">
        <span class="k-row-body" style="flex: 1 1 220px"><b><button class="link" @click="emit('open', r.student_id)">{{ r.name }}</button></b>
          <span class="k-meta">{{ r.course }} ← {{ r.next }}</span>
          <span v-if="r.class" class="k-meta">پیشنهاد: {{ r.class.pair_text }} ساعت {{ fa(r.class.time) }} با {{ r.class.teacher }} · {{ fa(r.class.free) }} جای خالی</span></span>
        <span class="k-btns">
          <button class="btn sm" @click="emit('message', { student_id: r.student_id, kind: 'renew' })"><Icon name="message" :size="14" />پیام</button>
          <button v-if="r.class" class="btn primary sm" :disabled="busy === r.student_id || r.class.free <= 0" @click="enrol(r)">ثبت‌نام</button>
        </span>
      </li>
    </ul>
  </div>
</template>
