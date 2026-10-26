<script setup>
// The three Excel files the assistant works from. Each can be looked at, downloaded as it is now
// (new invoices from the phone desk are already in it), or replaced with your own version.
import { ref, computed, watch, onMounted } from "vue"
import { api, fa, fabricSession, lockScroll } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { num } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const LOOK = {
  stock: { icon: "inbox", what: "جنس‌ها، توپ و متراژ، قیمت خرید و فروش، تأمین‌کننده" },
  sales: { icon: "chart", what: "هر قلم فاکتور: تاریخ، مشتری، جنس، متراژ، مبلغ و نوع پرداخت" },
  accounts: { icon: "file", what: "مشتری‌ها و سقف اعتبار، دریافتی‌ها، چک‌های دریافتی و پرداختی، بانک" },
}
const d = ref(null), view = ref(null), sheet = ref(0), uploading = ref("")
const canUpload = computed(() => ["owner", "accountant"].includes(fabricSession.user?.role))
const load = async () => { d.value = await api("/fabric/files") }
onMounted(load)
watch(() => !!view.value, lockScroll)

const open = async (f) => { view.value = { file: f, sheets: null }; sheet.value = 0; view.value.sheets = await api(`/fabric/files/${f.key}/preview`) }
const download = async (f) => {
  const res = await fetch(`/fabric/files/${f.key}/download`, { headers: { Authorization: `Bearer ${fabricSession.token}` } })
  if (!res.ok) return toast({ tone: "danger", title: "دانلود نشد" })
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement("a"); a.href = url; a.download = f.name; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
const upload = async (f, e) => {
  const file = e.target.files[0]; e.target.value = ""
  if (!file) return
  uploading.value = f.key
  try {
    const data = await new Promise((ok, bad) => {
      const r = new FileReader(); r.onload = () => ok(String(r.result).split(",")[1]); r.onerror = bad; r.readAsDataURL(file)
    })
    const res = await api(`/fabric/files/${f.key}`, { data })
    toast({ tone: "success", title: `${f.name} خوانده شد`, body: `${fa(res.products)} جنس، ${fa(res.customers)} مشتری و ${fa(res.invoices)} فاکتور.` })
    await load()
  } catch (err) {
    toast({ tone: "danger", title: "فایل خوانده نشد", body: err.message + " فایل قبلی سر جایش ماند." })
  } finally { uploading.value = "" }
}
const cell = (v) => typeof v === "number" ? num(v) : fa(v)
</script>

<template>
  <div class="flex flex-col gap-6">
    <section v-reveal>
      <h2>فایل‌های اکسل</h2>
      <p class="muted">دستیار همه‌ی عددها را از همین سه فایل حساب می‌کند. فاکتورهایی که پشت تلفن ثبت می‌شوند به همین فایل‌ها اضافه می‌شوند.</p>
    </section>
    <div v-if="!d" class="grid md:grid-cols-3 gap-4"><div v-for="n in 3" :key="n" class="card"><Skeleton :lines="4" /></div></div>
    <div v-else class="grid md:grid-cols-3 gap-4 sm:gap-6">
      <article v-for="f in d.files" :key="f.key" v-reveal class="card xf-card">
        <div class="xf-top">
          <span class="xf-icon"><Icon :name="LOOK[f.key].icon" :size="24" /><i>XLSX</i></span>
          <div><b>فایل {{ f.name.replace('.xlsx', '') }}</b><small class="muted">اکسل · {{ fa(Math.round(f.size / 1024)) }} کیلوبایت</small></div>
        </div>
        <p class="small muted">{{ LOOK[f.key].what }}</p>
        <div class="xf-sheets"><span v-for="s in f.sheets" :key="s.name" class="chip">{{ s.name }} · {{ fa(s.total) }} ردیف</span></div>
        <div class="btn-row">
          <button class="btn sm primary" @click="open(f)"><Icon name="search" :size="16" />دیدن</button>
          <button class="btn sm ghost" @click="download(f)">دانلود</button>
          <label v-if="canUpload" class="btn sm ghost xf-up">
            <template v-if="uploading === f.key"><span class="dots"><i></i><i></i><i></i></span></template>
            <template v-else>نسخه‌ی خودم</template>
            <input type="file" accept=".xlsx" :disabled="!!uploading" @change="upload(f, $event)" aria-label="بارگذاری نسخه‌ی جدید">
          </label>
        </div>
      </article>
    </div>

    <section v-if="d && d.notes.length" v-reveal class="card">
      <div class="card-head"><Icon name="sparkles" :size="18" class="text-primary" />دستیار موقع خواندن فایل‌ها این‌ها را مرتب کرد</div>
      <ul class="xf-notes"><li v-for="n in d.notes" :key="n"><Icon name="check" :size="16" />{{ fa(n) }}</li></ul>
    </section>

    <div v-if="view" class="overlay" @click.self="view = null">
      <aside class="drawer xf-drawer" v-drawer :aria-label="view.file.name">
        <div class="drawer-head">
          <b class="text-ink">فایل {{ view.file.name.replace('.xlsx', '') }}</b>
          <button class="icon-btn" @click="view = null" aria-label="بستن"><Icon name="x" /></button>
        </div>
        <div class="drawer-body" tabindex="0">
          <Skeleton v-if="!view.sheets" :lines="10" />
          <template v-else>
            <div class="segmented xf-tabs" role="tablist">
              <button v-for="(s, i) in view.sheets" :key="s.name" role="tab" :aria-selected="sheet === i" :class="{ on: sheet === i }" @click="sheet = i">{{ s.name }}</button>
            </div>
            <div class="xf-table-wrap" tabindex="0">
              <table class="xf-table">
                <thead><tr><th v-for="h in view.sheets[sheet].header" :key="h">{{ h }}</th></tr></thead>
                <tbody><tr v-for="(r, i) in view.sheets[sheet].rows" :key="i"><td v-for="(v, j) in r" :key="j">{{ cell(v) }}</td></tr></tbody>
              </table>
            </div>
            <p v-if="view.sheets[sheet].total > view.sheets[sheet].rows.length" class="muted small">
              {{ fa(view.sheets[sheet].rows.length) }} ردیف {{ view.sheets[sheet].latest ? 'آخر' : 'اول' }} از {{ fa(view.sheets[sheet].total) }} ردیف. برای همه، فایل را دانلود کنید.</p>
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>
