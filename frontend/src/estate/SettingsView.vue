<script setup>
// «تنظیمات» (owner only): the deposit-to-rent rate and the commission tariff the whole assistant works with.
// The defaults follow common Tehran practice; a real agency checks them against its union's tariff for this year.
import { reactive, ref, onMounted } from "vue"
import { api } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
import Converter from "./Converter.vue"

const s = reactive({ rate: "", sale_fee: "", rent_fee: "" }), busy = ref(false), error = ref("")
onMounted(async () => Object.assign(s, await api("/estate/settings")))
async function save() {
  busy.value = true; error.value = ""
  try { Object.assign(s, await api("/estate/settings", { rate: Number(s.rate), sale_fee: Number(s.sale_fee), rent_fee: Number(s.rent_fee) })); toast({ tone: "success", title: "تنظیمات ذخیره شد" }) }
  catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "عددها درست نیست" : e.message } finally { busy.value = false }
}
</script>

<template>
  <div class="grid grid-cols-12 gap-6">
    <form class="card col-span-12 lg:col-span-6 flex flex-col gap-3" @submit.prevent="save">
      <div class="card-head">نرخ‌ها و تعرفه</div>
      <label class="field"><span>نرخ تبدیل ودیعه به اجاره (درصد در ماه)</span><input v-model="s.rate" inputmode="decimal"><small class="muted">۳ یعنی هر یک میلیون تومان ودیعه برابر ۳۰ هزار تومان اجاره در ماه است.</small></label>
      <label class="field"><span>کمیسیون فروش (درصد قیمت، از هر طرف)</span><input v-model="s.sale_fee" inputmode="decimal"></label>
      <label class="field"><span>کمیسیون اجاره (درصد اجاره‌ی یک ماه با ودیعه‌ی تبدیل‌شده، از هر طرف)</span><input v-model="s.rent_fee" inputmode="decimal"></label>
      <p class="check info small"><Icon name="info" :size="14" /><span>این عددها پیش‌فرض است. آن‌ها را با تعرفه‌ی امسال اتحادیه‌ی مشاوران املاک شهر خود تطبیق دهید.</span></p>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div><button class="btn primary" :disabled="busy">ذخیره</button></div>
    </form>
    <div class="col-span-12 lg:col-span-6"><Converter /></div>
  </div>
</template>
