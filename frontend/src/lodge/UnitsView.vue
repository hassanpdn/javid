<script setup>
// «واحدها»: every unit with its picture, prices and state. The host makes a new one, edits it (name, kind, beds,
// capacity, weekday and weekend price, description, what it has, its drawing), adds or removes photos (the server
// shrinks them), switches it off (gone from the website and from sale; its bookings stay), and closes nights.
import { ref, reactive, onMounted } from "vue"
import { api, fa, lodgeSession, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { lodgeInfo, digits } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import DatePicker from "../components/core/DatePicker.vue"
import Art from "../eco/Art.vue"

const emit = defineEmits(["changed"])
const host = lodgeSession.user.role === "host"
const list = ref(null), edit = ref(null), busy = ref(0), block = reactive({ id: 0, start: null, end: null, note: "" })
const load = async () => { list.value = await api("/lodge/units") }
onMounted(() => retryable(load))
const blank = { name: "", kind: "dome", beds: 2, capacity: 3, price: "", weekend_price: "", description: "", amenities: "", art: "dome" }
const open = (u) => { edit.value = u ? { id: u.id, ...Object.fromEntries(Object.keys(blank).map((k) => [k, u[k]])), amenities: u.amenities.join("، ") } : { ...blank } }
async function run(key, path, body, title) {
  busy.value = key
  try { const r = await api(path, body); toast({ tone: "success", title: typeof title === "function" ? title(r) : title }); await load(); emit("changed"); return true }
  catch (e) { toast({ tone: "danger", title: typeof e.message === "string" && e.message.startsWith("[") ? "خانه‌ها را درست پر کنید" : e.message }) } finally { busy.value = 0 }
}
async function save() {
  const u = edit.value, body = { ...u, price: digits(u.price), weekend_price: digits(u.weekend_price), beds: Number(u.beds), capacity: Number(u.capacity) }
  delete body.id
  if (await run(-1, u.id ? `/lodge/units/${u.id}` : "/lodge/units", body, "ذخیره شد")) edit.value = null
}
const toggle = (u) => run(u.id, `/lodge/units/${u.id}/active`, { active: !u.active }, (r) => u.active ? `از سایت برداشته شد${r.bookings_left ? `؛ ${fa(r.bookings_left)} رزرو آینده‌اش سر جایش است` : ""}` : "دوباره در سایت است")
const photo = (u, e) => {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 6 * 1024 * 1024) { toast({ tone: "danger", title: "عکس بیش از ۶ مگابایت است" }); return }
  const r = new FileReader(); r.onload = () => run(u.id, `/lodge/units/${u.id}/photos`, { data: r.result }, "عکس اضافه شد"); r.readAsDataURL(file)
}
const delPhoto = (u, p) => run(u.id, `/lodge/photos/${p.id}/delete`, {}, "عکس برداشته شد")
const close = (u) => run(u.id, `/lodge/units/${u.id}/blocks`, { start: block.start, end: block.end, note: block.note }, "این شب‌ها بسته شد").then((ok) => { if (ok) block.id = 0 })
const open_ = (u, k) => run(u.id, `/lodge/blocks/${k.id}/delete`, {}, "شب‌ها دوباره باز شد")
</script>

<template>
  <div class="flex flex-col gap-4">
    <div v-if="host" class="btn-row"><button class="btn primary" @click="open(null)"><Icon name="plus" :size="18" />واحد جدید</button></div>
    <section v-if="edit" class="card flex flex-col gap-3">
      <div class="card-head">{{ edit.id ? 'ویرایش ' + edit.name : 'واحد جدید' }}</div>
      <div class="k-grid2">
        <label class="field"><span>نام</span><input v-model="edit.name" maxlength="40"></label>
        <label class="field"><span>نوع</span><select v-model="edit.kind" class="k-select"><option v-for="(t, k) in lodgeInfo.kinds" :key="k" :value="k">{{ t }}</option></select></label>
      </div>
      <div class="k-grid2">
        <label class="field"><span>تخت (نفر)</span><input v-model="edit.beds" type="number" min="1" max="20"></label>
        <label class="field"><span>ظرفیت با تشک اضافه</span><input v-model="edit.capacity" type="number" min="1" max="30"></label>
      </div>
      <div class="k-grid2">
        <label class="field"><span>قیمت هر شب (تومان)</span><input v-model="edit.price" inputmode="numeric"></label>
        <label class="field"><span>شب چهارشنبه و پنجشنبه (تومان)</span><input v-model="edit.weekend_price" inputmode="numeric"></label>
      </div>
      <label class="field"><span>توضیح کوتاه برای سایت</span><input v-model="edit.description" maxlength="400"></label>
      <label class="field"><span>امکانات (با ویرگول جدا کنید)</span><input v-model="edit.amenities" maxlength="300" placeholder="حمام اختصاصی، صبحانه‌ی محلی، ایوان"></label>
      <div class="field"><span>نقاشی (وقتی عکس ندارد)</span>
        <div class="lo-arts"><button v-for="k in ['dome', 'court', 'family', 'tower', 'garden', 'roof']" :key="k" type="button" :class="{ on: edit.art === k }" :aria-pressed="edit.art === k" :aria-label="k" @click="edit.art = k"><Art :kind="k" /></button></div></div>
      <div class="btn-row"><button class="btn primary" :disabled="busy === -1 || edit.name.trim().length < 2" @click="save">ذخیره</button><button class="btn ghost" @click="edit = null">انصراف</button></div>
    </section>

    <Skeleton v-if="!list" kind="row" :count="6" />
    <ul v-else class="lo-units" data-tour="lo-units">
      <li v-for="u in list" :key="u.id" :class="['card', 'lo-unit', { off: !u.active }]">
        <div class="lo-pic"><img v-if="u.photos.length" :src="u.photos[0]" :alt="u.name" loading="lazy"><Art v-else :kind="u.art" />
          <span :class="['tag', u.active ? 'k-t-success' : 'k-t-secondary']">{{ u.active ? 'در سایت' : 'خاموش' }}</span></div>
        <div class="lo-unit-body">
          <div class="k-row-top"><b>{{ u.name }}</b><small class="muted">{{ u.kind_text }}</small></div>
          <small class="muted">{{ fa(u.beds) }} تخت · تا {{ fa(u.capacity) }} نفر · هر شب {{ fa(u.price_text) }} · آخر هفته {{ fa(u.weekend_text) }}</small>
          <small class="muted">{{ fa(u.next) }} رزرو پیش رو<template v-if="u.rating.avg"> · ★ {{ fa(u.rating.avg) }} ({{ fa(u.rating.count) }})</template></small>
          <div v-if="u.blocks.length" class="flex flex-col gap-1"><small v-for="k in u.blocks" :key="k.id" class="k-late">بسته: {{ fa(k.text) }}<template v-if="k.note"> · {{ k.note }}</template>
            <button v-if="host" class="link small" style="margin-inline-start: 8px" @click="open_(u, k)">باز کردن</button></small></div>
          <div v-if="host && u.photo_ids.length" class="lo-photos"><figure v-for="p in u.photo_ids" :key="p.id"><img :src="'/lodge/public/photo/' + p.file" alt="">
            <button class="icon-btn sm" aria-label="برداشتن عکس" @click="delPhoto(u, p)"><Icon name="x" :size="14" /></button></figure></div>
          <div v-if="host" class="k-btns">
            <button class="btn sm" @click="open(u)"><Icon name="edit" :size="14" />ویرایش</button>
            <label class="btn ghost sm"><input type="file" accept="image/jpeg,image/png" hidden @change="photo(u, $event)"><Icon name="plus" :size="14" />عکس</label>
            <button class="btn ghost sm" @click="Object.assign(block, { id: u.id, start: lodgeInfo.today, end: null, note: '' })">بستن شب‌ها</button>
            <button class="btn ghost sm" :disabled="busy === u.id" @click="toggle(u)">{{ u.active ? 'خاموش کردن' : 'روشن کردن' }}</button>
          </div>
          <form v-if="block.id === u.id" class="flex flex-col gap-2" @submit.prevent="close(u)">
            <div class="k-grid2"><div class="field"><span>از شب</span><DatePicker v-model="block.start" label="از شب" /></div><div class="field"><span>تا روز</span><DatePicker v-model="block.end" :min="block.start" label="تا روز" /></div></div>
            <input v-model="block.note" class="k-search" maxlength="80" placeholder="چرا؟ مثلاً تعمیر یا مهمان خانواده" aria-label="دلیل">
            <div class="btn-row"><button class="btn primary sm" :disabled="!block.start || !block.end">بستن</button><button type="button" class="btn ghost sm" @click="block.id = 0">انصراف</button></div>
          </form>
        </div>
      </li>
    </ul>
  </div>
</template>
