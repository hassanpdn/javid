<script setup>
// «ثبت ابلاغیه»: paste the notice from the courts' system (ثنا). The assistant reads its kind, case number, branch and
// dates, shows the words each came from, and finds the case it belongs to. The secretary checks, saves, and sees the
// last day of what it asks for, worked out by the server with Fridays and holidays.
import { ref, reactive, computed, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { officeInfo, KINDS } from "./lib.js"
import Icon from "../components/Icon.vue"
import DatePicker from "../components/core/DatePicker.vue"
import TimePicker from "../components/core/TimePicker.vue"
import HowTip from "../fabric/HowTip.vue"

const emit = defineEmits(["close", "saved"])
const step = ref("text"), text = ref(""), busy = ref(false), error = ref(""), found = ref({}), method = ref(""), matches = ref([]), cases = ref([]), saved = ref(null)
const f = reactive({ case_id: null, kind: "", served: officeInfo.today, hearing_date: null, hearing_time: "10:00" })
onMounted(async () => { try { cases.value = await api("/law/cases") } catch {} })
const sample = async () => { try { text.value = (await api("/law/sample")).text } catch {} }
async function readText() {
  busy.value = true; error.value = ""
  try {
    const r = await api("/law/read", { text: text.value })
    Object.assign(f, { kind: r.fields.kind || "", served: r.fields.served || officeInfo.today, hearing_date: r.fields.hearing_date, hearing_time: r.fields.hearing_time || "10:00",
                       case_id: r.cases[0]?.id || null })
    found.value = r.found; method.value = r.method; matches.value = r.cases; step.value = "form"
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function save() {
  busy.value = true; error.value = ""
  try {
    saved.value = await api("/law/notices", { case_id: f.case_id, kind: f.kind, served: f.served, text: text.value,
                                             hearing_date: f.kind === "hearing" ? f.hearing_date : null, hearing_time: f.kind === "hearing" ? f.hearing_time : null })
    toast({ tone: "success", title: "ابلاغیه ثبت شد" })
  } catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "بعضی خانه‌ها درست پر نشده است" : e.message } finally { busy.value = false }
}
const ready = computed(() => f.case_id && f.kind && f.served && (f.kind !== "hearing" || (f.hearing_date && f.hearing_time)))
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog wide" v-pop role="dialog" aria-label="ثبت ابلاغیه">
      <div class="dialog-head"><h3>ثبت ابلاغیه</h3><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>

      <template v-if="saved">
        <p class="check ok small"><Icon name="check" :size="14" /><span>ابلاغیه در پرونده‌ی «{{ saved.case_title }}» ثبت شد.</span></p>
        <section v-if="saved.deadline" class="k-result">
          <div class="k-row-top"><b>روز آخر {{ saved.todo }}</b><HowTip v-if="saved.how" :lines="saved.how" /></div>
          <span class="k-big">{{ fa(saved.deadline_text) }}</span><small class="muted">{{ fa(saved.left_text) }}</small>
        </section>
        <section v-else-if="saved.hearing" class="k-result"><b>جلسه</b><span class="k-big">{{ fa(saved.hearing_text) }}</span></section>
        <div class="dialog-actions"><button class="btn primary" @click="emit('saved', saved.case_id)">دیدن پرونده</button><button class="btn ghost" @click="emit('close')">بستن</button></div>
      </template>

      <template v-else-if="step === 'text'">
        <p class="muted small">متن ابلاغیه را از سامانه‌ی ثنا کپی کنید و این‌جا بگذارید. دستیار نوع ابلاغیه، شماره‌ی پرونده، شعبه و تاریخ‌ها را درمی‌آورد و پرونده‌اش را پیدا می‌کند.</p>
        <textarea v-model="text" rows="8" maxlength="4000" placeholder="متن ابلاغیه…" aria-label="متن ابلاغیه"></textarea>
        <div class="btn-row"><button class="chip-btn" type="button" @click="sample"><Icon name="file" :size="14" />یک نمونه از پرونده‌های دفتر</button></div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="dialog-actions"><button class="btn primary" :disabled="busy || text.trim().length < 10" @click="readText"><Icon name="sparkles" :size="18" />{{ busy ? 'در حال خواندن…' : 'خواندن ابلاغیه' }}</button>
          <button class="btn ghost" @click="step = 'form'">پر کردن دستی</button></div>
      </template>

      <form v-else class="flex flex-col gap-3" @submit.prevent="save">
        <p v-if="method" class="check info small"><Icon name="info" :size="14" /><span>{{ method === 'model' ? 'دستیار متن را خواند' : 'متن با قاعده‌های ثابت خوانده شد' }}. هر چه در متن نبود خالی مانده است و زیر هر مقدار، جایی از متن که از آن آمده نوشته شده است.</span></p>
        <label class="field"><span>پرونده</span>
          <select v-model="f.case_id" class="k-select"><option :value="null" disabled>انتخاب کنید</option><option v-for="c in cases" :key="c.id" :value="c.id">{{ c.title }}</option></select>
          <small v-if="matches.length" class="k-from">پیدا شد: {{ matches[0].why }} («{{ fa(found.number || found.archive || '') }}»)</small>
          <small v-else-if="method" class="k-late">پرونده‌ای با این شماره پیدا نشد. از فهرست انتخاب کنید یا اول پرونده را باز کنید.</small></label>
        <label class="field"><span>نوع ابلاغیه</span>
          <select v-model="f.kind" class="k-select"><option value="" disabled>انتخاب کنید</option><option v-for="(t, k) in KINDS" :key="k" :value="k">{{ t }}</option></select>
          <small v-if="found.kind" class="k-from">از متن: «{{ fa(found.kind) }}»</small></label>
        <div class="field"><span>تاریخ ابلاغ</span><DatePicker v-model="f.served" :min="'1400/01/01'" label="تاریخ ابلاغ" />
          <small v-if="found.served" class="k-from">از متن: «{{ fa(found.served) }}»</small></div>
        <div v-if="f.kind === 'hearing'" class="k-grid2">
          <div class="field"><span>تاریخ جلسه</span><DatePicker v-model="f.hearing_date" label="تاریخ جلسه" /><small v-if="found.hearing_date" class="k-from">«{{ fa(found.hearing_date) }}»</small></div>
          <div class="field"><span>ساعت جلسه</span><TimePicker v-model="f.hearing_time" label="ساعت جلسه" /></div>
        </div>
        <p v-if="found.branch || found.court" class="muted small">شعبه و دادگاه در متن: {{ fa(found.court || found.branch) }}</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="dialog-actions"><button class="btn primary" :disabled="busy || !ready"><Icon name="check" :size="18" />ثبت و حساب مهلت</button>
          <button type="button" class="btn ghost" @click="step = 'text'">بازگشت به متن</button></div>
      </form>
    </div>
  </div>
</template>
