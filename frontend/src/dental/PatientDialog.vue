<script setup>
// «بیمار جدید»: a name and a mobile number. A number already on file says whose it is.
import { ref, reactive } from "vue"
import { api } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"

const emit = defineEmits(["close", "saved"])
const f = reactive({ name: "", phone: "" }), busy = ref(false), error = ref("")
async function save() {
  busy.value = true; error.value = ""
  try { const r = await api("/dental/patients", { ...f }); toast({ tone: "success", title: "پرونده‌ی بیمار باز شد" }); emit("saved", r.id) }
  catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "نام و شماره‌ی همراه را درست بنویسید" : e.message } finally { busy.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <form class="dialog" v-pop role="dialog" aria-label="بیمار جدید" @submit.prevent="save">
      <div class="dialog-head"><h3>بیمار جدید</h3><button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <label class="field"><span>نام و نام خانوادگی</span><input v-model="f.name" maxlength="60" required></label>
      <label class="field"><span>شماره‌ی همراه</span><input v-model="f.phone" dir="ltr" inputmode="tel" maxlength="20" placeholder="09121234567" required></label>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="dialog-actions"><button class="btn primary" :disabled="busy || f.name.trim().length < 3 || f.phone.trim().length < 10"><Icon name="check" :size="18" />باز کردن پرونده</button></div>
    </form>
  </div>
</template>
