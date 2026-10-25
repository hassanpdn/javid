<script setup>
// Counselor: one student's file, opened in a side drawer
import { ref, computed, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { schoolInfo } from "../lib/school.js"
import Icon from "./Icon.vue"
import Avatar from "./Avatar.vue"
import CountUp from "./CountUp.vue"
import TypeText from "./TypeText.vue"
import Sparkline from "./Sparkline.vue"
import LevelChip from "./LevelChip.vue"

const props = defineProps(["sid"])
const emit = defineEmits(["close", "changed"])
const f = ref(null), insight = ref(""), draft = ref(null), drafting = ref(false), newNote = ref(""), error = ref("")
const sent = computed(() => (f.value?.suggestions || []).filter((s) => s.status === "approved"))
const load = async () => {
  f.value = await api(`/counselor/students/${props.sid}`)
  draft.value = f.value.suggestions.find((s) => s.status === "draft") || null
}
const suggest = async () => {
  drafting.value = true; error.value = ""
  try { draft.value = await api(`/counselor/students/${props.sid}/suggest`, {}) }
  catch (e) { error.value = e.message } finally { drafting.value = false }
}
const approve = async () => {
  await api(`/counselor/suggestions/${draft.value.id}/approve`, { for_counselor: draft.value.for_counselor, for_parent: draft.value.for_parent })
  await load(); emit("changed")
}
const dismiss = async () => { await api(`/counselor/suggestions/${draft.value.id}/dismiss`, {}); draft.value = null }
const addNote = async () => { await api(`/counselor/students/${props.sid}/notes`, { note: newNote.value }); newNote.value = ""; await load() }
onMounted(async () => {
  await load()
  try { insight.value = (await api(`/counselor/students/${props.sid}/insight`)).text } catch { insight.value = "جمع‌بندی در دسترس نیست." }
})
</script>

<template>
  <div class="overlay" @click.self="$emit('close')">
    <aside class="drawer wide-drawer" v-drawer :aria-label="f ? 'پرونده ' + f.name : 'پرونده دانش‌آموز'">
      <div class="drawer-head">
        <div class="head-person" v-if="f"><Avatar :name="f.name" :size="46" /><div><b>{{ f.name }}</b><small class="muted">کلاس {{ f.class }} · آموزگار: {{ f.teacher }}</small></div></div>
        <span v-else></span>
        <button class="icon-btn" @click="$emit('close')" aria-label="بستن"><Icon name="x" /></button>
      </div>
      <div v-if="!f" class="drawer-body"><div class="card"><div class="shimmer"><span></span><span></span><span style="width:60%"></span></div></div></div>
      <div v-else class="drawer-body">

        <section v-reveal class="card brief">
          <div class="card-head"><span class="bot-avatar sm"><Icon name="sparkles" :size="15" /></span> جمع‌بندی دستیار</div>
          <p v-if="insight"><TypeText :text="insight" /></p>
          <div v-else class="shimmer"><span></span><span style="width:70%"></span></div>
          <div v-if="f.signals.length" class="chips">
            <span v-for="s in f.signals" :key="s.text" :class="['sig', s.type]">{{ fa(s.text) }}</span>
          </div>
        </section>

        <section v-if="schoolInfo.features.parents" v-reveal class="card">
          <div class="card-head">پیام به ولی</div>
          <template v-if="draft">
            <p class="muted small">این متن را دستیار نوشته است. بخوانید، در صورت نیاز ویرایش کنید و بعد بفرستید.</p>
            <label class="field mt-3"><span>گام بعدی برای شما</span><textarea v-model="draft.for_counselor" rows="2" class="ai-draft"></textarea></label>
            <label class="field mt-3"><span>پیام برای ولی</span><textarea v-model="draft.for_parent" rows="5" class="ai-draft"></textarea></label>
            <div class="dialog-actions mt-3">
              <button class="btn primary" :disabled="!draft.for_parent.trim()" @click="approve"><Icon name="send" :size="18" />تأیید و ارسال به ولی</button>
              <button class="btn ghost" @click="dismiss">کنار گذاشتن</button>
            </div>
          </template>
          <template v-else>
            <p class="muted small mb-3" v-if="!sent.length">هنوز پیامی برای ولیِ {{ f.first_name }} فرستاده نشده.</p>
            <div v-for="s in sent" :key="s.id" class="sent-msg">
              <small class="ok">✓ ارسال شد · {{ fa(s.approved_at) }}</small>
              <p class="ai-draft">{{ fa(s.for_parent) }}</p>
              <small v-if="s.for_counselor" class="muted">گام شما: {{ fa(s.for_counselor) }}</small>
            </div>
            <button class="btn" :disabled="drafting" @click="suggest"><Icon name="sparkles" :size="18" />{{ drafting ? 'دستیار در حال نوشتن...' : 'نوشتن پیام با دستیار' }}</button>
            <p v-if="error" class="error-text mt-2">{{ error }}</p>
          </template>
        </section>

        <section v-reveal class="card">
          <div class="card-head">پیشرفت درسی <small>از مهر تا امروز</small></div>
          <div class="progress-list">
            <div v-for="p in f.progress" :key="p.subject" class="prog-row">
              <span class="prog-sub">{{ p.subject }}</span>
              <Sparkline :points="p.points" :change="p.change" />
              <LevelChip :level="p.now" />
            </div>
            <!-- the time axis under the trend lines: oldest on the right, today on the left -->
            <div class="prog-row prog-axis" aria-hidden="true"><span></span><span class="axis"><span>مهر</span><span>امروز</span></span><span></span></div>
          </div>
          <p v-for="p in f.progress.filter(p => p.note)" :key="'n' + p.subject" class="teacher-note">یادداشت آموزگار ({{ p.subject }}): {{ p.note }}</p>
        </section>

        <section v-reveal class="card">
          <div class="card-head">حضور <small>۳۰ روز اخیر</small></div>
          <div class="mini-stats">
            <div class="ok-tile"><b><CountUp :value="f.attendance.present" /></b><small>روز حاضر</small></div>
            <div :class="{ warn: f.attendance.unexcused >= 3 }"><b><CountUp :value="f.attendance.absent" /></b><small>غیبت ({{ fa(f.attendance.unexcused) }} غیرموجه)</small></div>
            <div><b><CountUp :value="f.attendance.late" /></b><small>تأخیر</small></div>
          </div>
          <div v-if="f.attendance.absent_days.length" class="chips">
            <span v-for="d in f.attendance.absent_days" :key="d.date" :class="['day', { ok: d.excused }]">{{ fa(d.date) }}{{ d.excused ? ' · موجه' : '' }}</span>
          </div>
        </section>

        <section v-reveal class="card">
          <div class="card-head">فرم‌های سلامت <small>تکمیل‌شده توسط ولی</small></div>
          <div class="forms-grid">
            <div v-for="k in ['physical', 'wellbeing']" :key="k" class="form-tile">
              <b>{{ k === 'physical' ? 'سلامت جسمی' : 'حال و احوال' }}</b>
              <template v-if="f.forms[k]">
                <small class="muted">{{ fa(f.forms[k].date) }}</small>
                <div class="chips"><span v-for="fl in f.forms[k].flags" :key="fl" class="sig health">{{ fa(fl) }}</span>
                  <span v-if="!f.forms[k].flags.length" class="sig ok">مورد قابل توجهی ندارد</span></div>
                <details><summary class="small">پاسخ‌ها</summary>
                  <dl class="answers"><template v-for="[key, label] in f.fields[k]" :key="key"><dt>{{ label }}</dt><dd>{{ fa(f.forms[k].data[key] ?? '-') }}</dd></template></dl>
                </details>
              </template>
              <small v-else class="muted">هنوز تکمیل نشده</small>
            </div>
          </div>
        </section>

        <section v-reveal class="card">
          <div class="card-head">یادداشت‌های مشاور <small>فقط برای شما، ولی این‌ها را نمی‌بیند</small></div>
          <form class="note-add" @submit.prevent="addNote">
            <textarea v-model="newNote" rows="2" placeholder="یادداشت جدید..." aria-label="یادداشت جدید"></textarea>
            <button class="btn" :disabled="!newNote.trim()">ثبت</button>
          </form>
          <ul class="notes"><li v-for="(n, i) in f.notes" :key="i"><small class="muted">{{ fa(n.date) }}</small><p>{{ fa(n.note) }}</p></li></ul>
        </section>
      </div>
    </aside>
  </div>
</template>
