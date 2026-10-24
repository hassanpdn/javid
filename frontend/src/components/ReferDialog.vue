<script setup>
// Refer a letter to people. The assistant suggests recipients; for parents it writes a simple message.
import { ref, reactive, computed, watch, onMounted } from "vue"
import { api, fa } from "../lib/api.js"
import Icon from "./Icon.vue"

const props = defineProps(["letter"])
const emit = defineEmits(["close", "done"])
const options = ref({ groups: [], people: [] })
const picked = ref([]), q = ref(""), note = ref(""), needsAck = ref(true), sending = ref(false), error = ref("")
const suggestion = reactive({ loading: true, keys: [], reason: "" })
const parent = reactive({ loading: false, text: "" })
const all = computed(() => [...options.value.groups, ...options.value.people])
const find = (k) => all.value.find((p) => p.key === k)
const label = (k) => find(k)?.label || k
const kindOf = (k) => find(k)?.kind || "staff"
const match = (p) => !q.value.trim() || (p.label + " " + (p.sub || "")).includes(q.value.trim())
const sections = computed(() => [
  { title: "گروه‌ها", items: options.value.groups.filter(match) },
  { title: "کارکنان و معلمان", items: options.value.people.filter((p) => p.kind !== "parent" && match(p)) },
  { title: "اولیا", items: options.value.people.filter((p) => p.kind === "parent" && match(p)) },
])
const hasParents = computed(() => picked.value.some((k) => kindOf(k) === "parent"))
// rough head count for the button label
const estimate = computed(() => picked.value.reduce((n, k) => n + (
  k === "group:parents" ? options.value.people.filter((p) => p.kind === "parent").length :
  k === "group:teachers" ? options.value.people.filter((p) => p.kind === "teacher").length :
  k.startsWith("group:class:") ? 15 : 1), 0))
const toggle = (k) => { picked.value = picked.value.includes(k) ? picked.value.filter((x) => x !== k) : [...picked.value, k] }
const applySuggestion = () => { picked.value = [...new Set([...picked.value, ...suggestion.keys])] }
const draftParent = async () => {
  parent.loading = true
  try { parent.text = (await api(`/staff/letters/${props.letter.id}/parent-draft`, {})).text } catch {}
  finally { parent.loading = false }
}
// the first time a parent group is picked, the agent writes the parent message automatically
watch(hasParents, (v) => { if (v && !parent.text) draftParent() })
const send = async () => {
  sending.value = true; error.value = ""
  try {
    await api(`/staff/letters/${props.letter.id}/refer`,
      { recipients: picked.value, note: note.value, needs_ack: needsAck.value, parent_text: parent.text })
    emit("done")
  } catch (e) { error.value = e.message } finally { sending.value = false }
}
onMounted(async () => {
  options.value = await api("/staff/recipients")
  try { Object.assign(suggestion, await api(`/staff/letters/${props.letter.id}/suggest`, {})) } catch {}
  suggestion.loading = false
})
</script>

<template>
  <div class="overlay" @click.self="$emit('close')">
    <form class="dialog wide" v-pop @submit.prevent="send">
      <div class="dialog-head">
        <div><h3>ارجاع نامه</h3><p class="muted small">{{ fa(letter.subject) }}</p></div>
        <button type="button" class="icon-btn" @click="$emit('close')" aria-label="بستن"><Icon name="x" /></button>
      </div>

      <div class="suggest">
        <span class="bot-avatar sm"><Icon name="sparkles" :size="15" /></span>
        <div v-if="suggestion.loading" class="muted small flex-1">دستیار در حال پیشنهاد گیرنده<span class="dots"><i></i><i></i><i></i></span></div>
        <div v-else-if="suggestion.keys.length" class="suggest-body">
          <span class="small">پیشنهاد دستیار: <b>{{ suggestion.keys.map(label).join('، ') }}</b></span>
          <small class="muted" v-if="suggestion.reason">{{ fa(suggestion.reason) }}</small>
        </div>
        <div v-else class="muted small">دستیار پیشنهادی نداشت. گیرنده را خودتان انتخاب کنید.</div>
        <button v-if="suggestion.keys.length" type="button" class="btn sm primary" @click="applySuggestion">اعمال پیشنهاد</button>
      </div>

      <div class="picked">
        <span v-if="!picked.length" class="muted small">هنوز گیرنده‌ای انتخاب نشده.</span>
        <span v-for="k in picked" :key="k" v-pop:drop :class="['pick', kindOf(k)]">{{ label(k) }}<button type="button" @click="toggle(k)" aria-label="حذف">×</button></span>
      </div>

      <input class="search" v-model="q" placeholder="جستجوی نام، درس یا نام دانش‌آموز...">
      <div class="people">
        <template v-for="sec in sections" :key="sec.title">
          <div v-if="sec.items.length" class="people-sec">{{ sec.title }}</div>
          <button v-for="p in sec.items" :key="p.key" type="button" :class="['person', { on: picked.includes(p.key) }]" @click="toggle(p.key)">
            <span class="check-box">{{ picked.includes(p.key) ? '✓' : '' }}</span>
            <span class="person-text"><b>{{ p.label }}</b><small v-if="p.sub" class="muted">{{ p.sub }}</small></span>
          </button>
        </template>
      </div>

      <label class="field"><span>یادداشت برای گیرندگان <span class="muted">(اختیاری)</span></span>
        <textarea v-model="note" rows="2" placeholder="مثلا: لطفا تا ۳ دی دو دانش‌آموز معرفی کنید."></textarea></label>

      <div v-if="hasParents" class="parent-box">
        <div class="row-between"><b class="small text-ink">پیام برای اولیا</b>
          <button type="button" class="link small" @click="draftParent" :disabled="parent.loading">{{ parent.loading ? 'در حال نوشتن...' : 'نوشتن دوباره با دستیار' }}</button></div>
        <p class="muted small">اولیا متن اداری نامه را نمی‌بینند؛ فقط این پیام ساده را دریافت می‌کنند.</p>
        <div v-if="parent.loading && !parent.text" class="shimmer"><span></span><span></span><span style="width:60%"></span></div>
        <textarea v-else v-model="parent.text" rows="5"></textarea>
      </div>

      <label class="ack-row"><input type="checkbox" v-model="needsAck"> گیرندگان باید «رؤیت شد» را بزنند</label>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="dialog-actions">
        <button class="btn primary" type="submit" :disabled="!picked.length || sending || (hasParents && !parent.text.trim())">
          <Icon name="send" :size="18" />ارجاع به {{ fa(estimate) }} نفر</button>
        <button class="btn ghost" type="button" @click="$emit('close')">انصراف</button>
      </div>
    </form>
  </div>
</template>
