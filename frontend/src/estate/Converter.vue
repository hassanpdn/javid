<script setup>
// «تبدیل ودیعه و اجاره»: the same unit with another deposit. The server works it out with the agency's rate.
import { ref, reactive } from "vue"
import { api, fa } from "../lib/api.js"
import { fromMillions } from "./lib.js"
import Icon from "../components/Icon.vue"
import HowTip from "../fabric/HowTip.vue"

const f = reactive({ deposit: "500", rent: "15", new_deposit: "300" }), r = ref(null), error = ref("")
async function run() {
  error.value = ""
  try { r.value = await api("/estate/convert", { deposit: fromMillions(f.deposit), rent: fromMillions(f.rent), new_deposit: fromMillions(f.new_deposit) }) }
  catch (e) { error.value = e.message }
}
</script>

<template>
  <section class="card">
    <div class="card-head"><span class="grow">تبدیل ودیعه و اجاره <small>میلیون تومان</small></span><HowTip v-if="r" :lines="r.how" /></div>
    <form class="es-grid3" @submit.prevent="run">
      <label class="field"><span>ودیعه‌ی فعلی</span><input v-model="f.deposit" inputmode="numeric"></label>
      <label class="field"><span>اجاره‌ی فعلی</span><input v-model="f.rent" inputmode="numeric"></label>
      <label class="field"><span>ودیعه‌ی جدید</span><input v-model="f.new_deposit" inputmode="numeric"></label>
      <button class="btn sm es-span"><Icon name="refresh" :size="14" />حساب کن</button>
    </form>
    <p v-if="r" class="es-verdict fair"><Icon name="check" :size="16" />{{ fa(r.text) }}</p>
    <p v-if="error" class="error-text">{{ error }}</p>
  </section>
</template>
