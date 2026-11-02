<script setup>
// A new listing (kind "listing") or buyer (kind "request") from any text: paste a Divar ad, a WhatsApp message or the
// notes of a call, the assistant fills the form, and under each value it shows the line of the text it came from.
// What the text did not say stays empty; the agent fills or fixes it and saves. For a listing, units that look the
// same are shown before saving.
import { ref, reactive, computed } from "vue"
import { api, fa } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { agencyInfo, KINDS, FEATURES, toMillions, fromMillions } from "./lib.js"
import Icon from "../components/Icon.vue"

const props = defineProps({ kind: { default: "listing" } })
const emit = defineEmits(["close", "saved"])
const listing = computed(() => props.kind === "listing")
const step = ref("text"), text = ref(""), busy = ref(false), error = ref(""), found = ref({}), method = ref(""), dups = ref([])
const f = reactive({ kind: "", hood: "", hoods: [], street: "", area: "", rooms: "", floor: "", floors: "", age: "", elevator: false, parking: false,
                     storage: false, price: "", deposit: "", rent: "", budget: "", owner_name: "", owner_phone: "", name: "", phone: "", note: "" })
const SAMPLES = {
  listing: "رهن و اجاره، سعادت‌آباد، خیابان کاج\nآپارتمان ۱۱۰ متری سه خوابه، طبقه چهارم از شش طبقه، ۸ سال ساخت\nآسانسور و پارکینگ دارد، بدون انباری\nرهن ۸۰۰ میلیون، اجاره ماهی ۲۵ میلیون\nمالک: آقای سهراب نوری ۰۹۱۲۴۴۵۸۸۲۱",
  request: "خانم شیما طاهری ۰۹۳۵۱۲۲۶۶۴۰ زنگ زد، دنبال اجاره در جنت‌آباد یا شهران، دو خواب، رهن ۴۰۰ میلیون و اجاره تا ۱۵ میلیون، پارکینگ لازم دارد",
}
async function readText() {
  busy.value = true; error.value = ""
  try {
    const r = await api("/estate/read", { kind: props.kind, text: text.value })
    const v = r.fields
    for (const k of ["kind", "hood", "street", "area", "rooms", "floor", "floors", "age", "owner_name", "owner_phone", "name", "phone"]) f[k] = v[k] ?? ""
    for (const k of Object.keys(FEATURES)) f[k] = !!v[k]
    f.hoods = v.hoods || []
    for (const k of ["price", "deposit", "rent", "budget"]) f[k] = toMillions(v[k])
    f.note = text.value.trim().slice(0, 500)
    found.value = r.found; method.value = r.method; dups.value = r.duplicates || []
    step.value = "form"
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
const toggleHood = (h) => { f.hoods = f.hoods.includes(h) ? f.hoods.filter((x) => x !== h) : [...f.hoods, h] }
const n = (v) => Number(String(v ?? "").replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d))) || 0
async function save() {
  busy.value = true; error.value = ""
  try {
    const body = listing.value
      ? { kind: f.kind, hood: f.hood, street: f.street, area: n(f.area), rooms: n(f.rooms), floor: n(f.floor), floors: n(f.floors) || null, age: n(f.age),
          elevator: f.elevator, parking: f.parking, storage: f.storage, price: fromMillions(f.price), deposit: fromMillions(f.deposit), rent: fromMillions(f.rent),
          owner_name: f.owner_name, owner_phone: f.owner_phone, note: f.note }
      : { kind: f.kind, name: f.name, phone: f.phone, hoods: f.hoods, budget: fromMillions(f.budget), deposit: fromMillions(f.deposit), rent: fromMillions(f.rent),
          rooms: n(f.rooms), area: n(f.area), needs: Object.keys(FEATURES).filter((k) => f[k]), note: f.note }
    const r = await api(listing.value ? "/estate/listings" : "/estate/requests", body)
    toast({ tone: "success", title: listing.value ? `فایل ${fa(r.id)} ثبت شد` : "متقاضی ثبت شد",
            body: r.matches ? `${fa(r.matches)} ${listing.value ? "متقاضی با این فایل جور است" : "فایل با خواسته‌ی او جور است"}` : "فعلاً موردی جور نیست" })
    emit("saved", r)
  } catch (e) { error.value = typeof e.message === "string" && e.message.startsWith("[") ? "بعضی خانه‌ها درست پر نشده است" : e.message }
  finally { busy.value = false }
}
const from = (k) => found.value[k]
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog wide" v-pop role="dialog" :aria-label="listing ? 'فایل جدید' : 'متقاضی جدید'">
      <div class="dialog-head"><h3>{{ listing ? 'فایل جدید' : 'متقاضی جدید' }}</h3><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>

      <template v-if="step === 'text'">
        <p class="muted small">{{ listing ? 'آگهی دیوار، پیام واتس‌اپ یا یادداشت تماس مالک' : 'یادداشت تماس یا پیام متقاضی' }} را همان‌طور که هست این‌جا بگذارید. دستیار مشخصات را درمی‌آورد و شما پیش از ثبت آن‌ها را می‌بینید.</p>
        <textarea v-model="text" rows="7" maxlength="3000" :placeholder="listing ? 'مثلاً: ۹۲ متر دو خواب پونک، طبقه سوم، رهن ۵۰۰ اجاره ۱۳ ...' : 'مثلاً: آقای رحیمی، خرید دو خواب در پونک تا ۸ میلیارد ...'" aria-label="متن"></textarea>
        <div class="btn-row"><button class="chip-btn" type="button" @click="text = SAMPLES[kind]"><Icon name="file" :size="14" />یک نمونه</button></div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="dialog-actions"><button class="btn primary" :disabled="busy || text.trim().length < 5" @click="readText"><Icon name="sparkles" :size="18" />{{ busy ? 'در حال خواندن…' : 'خواندن متن' }}</button>
          <button class="btn ghost" @click="step = 'form'; f.note = text">پر کردن دستی</button></div>
      </template>

      <form v-else class="flex flex-col gap-3" @submit.prevent="save">
        <p v-if="method" class="check info small"><Icon name="info" :size="14" /><span>{{ method === 'model' ? 'دستیار متن را خواند' : 'متن با قاعده‌های ثابت خوانده شد' }}. هر مقداری که در متن نبود خالی مانده است؛ زیر هر مقدار، سطری از متن که از آن آمده نوشته شده است.</span></p>
        <div v-if="dups.length" class="check warn small"><Icon name="layers" :size="16" /><span>شاید این واحد قبلاً ثبت شده باشد:
          <template v-for="x in dups" :key="x.id"> فایل {{ fa(x.id) }} ({{ fa(x.title) }}، {{ fa(x.price_text) }}، {{ x.agent }}؛ {{ x.why }}).</template></span></div>

        <div class="es-seg" role="radiogroup" aria-label="نوع">
          <button v-for="(t, k) in KINDS" :key="k" type="button" role="radio" :aria-checked="f.kind === k" :class="{ on: f.kind === k }" @click="f.kind = k">{{ listing ? t : (k === 'sale' ? 'خرید' : 'رهن و اجاره') }}</button>
        </div>
        <small v-if="from('kind')" class="es-from">از متن: «{{ fa(from('kind')) }}»</small>

        <div v-if="listing" class="es-grid2">
          <label class="field"><span>محله</span><select v-model="f.hood" class="es-select"><option value="" disabled>انتخاب کنید</option><option v-for="h in agencyInfo.agency.hoods" :key="h">{{ h }}</option></select>
            <small v-if="from('hood')" class="es-from">از متن: «{{ fa(from('hood')) }}»</small></label>
          <label class="field"><span>خیابان</span><input v-model="f.street" maxlength="60"></label>
        </div>
        <div v-else class="field"><span>محله‌ها</span>
          <div class="es-chips"><button v-for="h in agencyInfo.agency.hoods" :key="h" type="button" :class="['chip-btn', { on: f.hoods.includes(h) }]" :aria-pressed="f.hoods.includes(h)" @click="toggleHood(h)">{{ h }}</button></div>
          <small v-if="from('hoods')" class="es-from">از متن: «{{ fa(from('hoods')) }}»</small></div>

        <div class="es-grid3">
          <label class="field"><span>{{ listing ? 'متراژ' : 'حداقل متراژ' }}</span><input v-model="f.area" inputmode="numeric"><small v-if="from('area')" class="es-from">«{{ fa(from('area')) }}»</small></label>
          <label class="field"><span>{{ listing ? 'خواب' : 'حداقل خواب' }}</span><input v-model="f.rooms" inputmode="numeric"><small v-if="from('rooms')" class="es-from">«{{ fa(from('rooms')) }}»</small></label>
          <template v-if="listing">
            <label class="field"><span>طبقه</span><input v-model="f.floor" inputmode="numeric"><small v-if="from('floor')" class="es-from">«{{ fa(from('floor')) }}»</small></label>
            <label class="field"><span>تعداد طبقات</span><input v-model="f.floors" inputmode="numeric"></label>
            <label class="field"><span>سن بنا (سال)</span><input v-model="f.age" inputmode="numeric"><small v-if="from('age')" class="es-from">«{{ fa(from('age')) }}»</small></label>
          </template>
        </div>
        <div class="es-chips">
          <label v-for="(t, k) in FEATURES" :key="k" class="es-check"><input v-model="f[k]" type="checkbox">{{ listing ? t : t + ' لازم دارد' }}</label>
        </div>

        <div class="es-grid3">
          <template v-if="f.kind === 'sale'">
            <label class="field"><span>{{ listing ? 'قیمت' : 'سقف بودجه' }} (میلیون تومان)</span><input v-model="f[listing ? 'price' : 'budget']" inputmode="numeric">
              <small v-if="from(listing ? 'price' : 'budget')" class="es-from">«{{ fa(from(listing ? 'price' : 'budget')) }}»</small></label>
          </template>
          <template v-else>
            <label class="field"><span>{{ listing ? 'ودیعه' : 'سقف ودیعه' }} (میلیون تومان)</span><input v-model="f.deposit" inputmode="numeric"><small v-if="from('deposit')" class="es-from">«{{ fa(from('deposit')) }}»</small></label>
            <label class="field"><span>{{ listing ? 'اجاره' : 'سقف اجاره' }} (میلیون تومان)</span><input v-model="f.rent" inputmode="numeric"><small v-if="from('rent')" class="es-from">«{{ fa(from('rent')) }}»</small></label>
          </template>
        </div>

        <div class="es-grid2">
          <label class="field"><span>{{ listing ? 'نام مالک' : 'نام متقاضی' }}</span><input v-model="f[listing ? 'owner_name' : 'name']" maxlength="60">
            <small v-if="from(listing ? 'owner_name' : 'name')" class="es-from">«{{ fa(from(listing ? 'owner_name' : 'name')) }}»</small></label>
          <label class="field"><span>تلفن همراه</span><input v-model="f[listing ? 'owner_phone' : 'phone']" dir="ltr" inputmode="tel" maxlength="20"></label>
        </div>
        <label class="field"><span>یادداشت</span><textarea v-model="f.note" rows="2" maxlength="500"></textarea></label>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="dialog-actions"><button class="btn primary" :disabled="busy"><Icon name="check" :size="18" />{{ listing ? 'ثبت فایل' : 'ثبت متقاضی' }}</button>
          <button type="button" class="btn ghost" @click="step = 'text'">بازگشت به متن</button></div>
      </form>
    </div>
  </div>
</template>
