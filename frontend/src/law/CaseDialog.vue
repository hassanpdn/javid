<script setup>
// «پرونده‌ی جدید»: the client, the subject, the other side, the court and branch, the case number, and the lawyer on it.
import { ref, reactive, onMounted } from "vue"
import { api, lawSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { FIELDS } from "./lib.js"
import Icon from "../components/Icon.vue"

const emit = defineEmits(["close", "saved"])
const lawyers = ref([]), busy = ref(false), error = ref("")
const f = reactive({ topic: "", client: "", phone: "", opponent: "", field: "civil", court: "", branch: "", number: "", archive: "",
                     lawyer_id: lawSession.user.role === "secretary" ? null : lawSession.user.id })
onMounted(async () => { lawyers.value = await api("/law/lawyers"); if (!f.lawyer_id) f.lawyer_id = lawyers.value[0]?.id })
async function save() {
  busy.value = true; error.value = ""
  try { const r = await api("/law/cases", { ...f }); toast({ tone: "success", title: "پرونده باز شد" }); emit("saved", r.id) }
  catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "خانه‌های لازم را پر کنید" : e.message } finally { busy.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <form class="dialog" v-pop role="dialog" aria-label="پرونده‌ی جدید" @submit.prevent="save">
      <div class="dialog-head"><h3>پرونده‌ی جدید</h3><button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div class="lw-grid2">
        <label class="field"><span>موکل</span><input v-model="f.client" maxlength="60" required></label>
        <label class="field"><span>تلفن موکل</span><input v-model="f.phone" dir="ltr" inputmode="tel" maxlength="20"></label>
      </div>
      <label class="field"><span>موضوع</span><input v-model="f.topic" maxlength="80" placeholder="مثلاً مطالبه‌ی وجه چک" required></label>
      <label class="field"><span>طرف دعوا</span><input v-model="f.opponent" maxlength="80"></label>
      <div class="lw-grid2">
        <label class="field"><span>نوع پرونده</span><select v-model="f.field" class="lw-select"><option v-for="(t, k) in FIELDS" :key="k" :value="k">{{ t }}</option></select></label>
        <label class="field"><span>وکیل مسئول</span><select v-model="f.lawyer_id" class="lw-select"><option v-for="l in lawyers" :key="l.id" :value="l.id">{{ l.name }}</option></select></label>
      </div>
      <div class="lw-grid2">
        <label class="field"><span>مرجع</span><input v-model="f.court" maxlength="80" placeholder="مثلاً دادگاه عمومی حقوقی تهران"></label>
        <label class="field"><span>شعبه</span><input v-model="f.branch" inputmode="numeric" maxlength="10"></label>
      </div>
      <div class="lw-grid2">
        <label class="field"><span>شماره‌ی پرونده</span><input v-model="f.number" dir="ltr" inputmode="numeric" maxlength="24"></label>
        <label class="field"><span>شماره‌ی بایگانی</span><input v-model="f.archive" dir="ltr" inputmode="numeric" maxlength="12"></label>
      </div>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="dialog-actions"><button class="btn primary" :disabled="busy || !f.client.trim() || !f.topic.trim()"><Icon name="check" :size="18" />باز کردن پرونده</button></div>
    </form>
  </div>
</template>
