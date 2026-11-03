<script setup>
// «تطبیق»: the three files checked against each other. Each finding shows, line by line, the sum that produced it
// and the sheet each number comes from, so it can be checked in the Excel files by hand. A finding is a place
// to look, not a verdict: the wording says what does not add up, never who did it. A shelf count that differs can be
// made the stock by the owner («اصلاح موجودی با این شمارش»): kept as an adjustment, written in the stock file and logged.
import { ref, onMounted } from "vue"
import { api, fa, retryable, fabricSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import FilesGlance from "./FilesGlance.vue"
import EventFeed from "./EventFeed.vue"

defineProps({ events: { type: Boolean, default: false } })
const d = ref(null), pulse = ref([])
const LOOK = { stock: ["inbox", "انبار و فروش"], invoice: ["file", "شماره فاکتورها"], cash: ["calendar", "صندوق و فروش نقدی"], cheque: ["file", "چک‌ها"],
               count: ["check", "شمارش قفسه"] }
const owner = fabricSession.user?.role === "owner"
const applying = ref(0), sure = ref(0)
async function apply(i) {
  applying.value = i.count_id
  try {
    await api(`/fabric/counts/${i.count_id}/apply`, {})
    toast({ tone: "success", title: "موجودی با شمارش اصلاح شد و در فایل انبار نوشته شد" })
    sure.value = 0; d.value = await api("/fabric/reconcile")
  } catch (e) { toast({ tone: "danger", title: e.message }) } finally { applying.value = 0 }
}
onMounted(() => retryable(async () => { d.value = await api("/fabric/reconcile") }))
const changed = async (files) => { pulse.value = files; d.value = await api("/fabric/reconcile"); setTimeout(() => { pulse.value = [] }, 2500) }
</script>

<template>
  <div class="flex flex-col gap-6">
    <section v-reveal>
      <h2>تطبیق سه فایل</h2>
      <p class="muted">دستیار فایل‌های انبار، فروش و حسابداری را با هم مقایسه می‌کند. هر جا با هم جور نباشند، اینجا با حسابش می‌آید.</p>
    </section>
    <div v-if="!d" class="card"><Skeleton :lines="5" /></div>
    <template v-else>
      <FilesGlance :glance="d" :pulse="pulse" compact />

      <section v-if="d.issues.length" class="flex flex-col gap-4">
        <h3 class="group-head">باید بررسی شود <span class="count">{{ fa(d.issues.length) }}</span></h3>
        <article v-for="i in d.issues" :key="i.kind + i.title" v-reveal class="card rc-issue">
          <div class="rc-top">
            <span class="tint t-danger"><Icon :name="LOOK[i.kind][0]" :size="20" /></span>
            <div class="grow"><small class="muted">{{ LOOK[i.kind][1] }}</small><b>{{ fa(i.title) }}</b></div>
          </div>
          <p class="small">{{ fa(i.detail) }}</p>
          <div class="rc-sum"><span v-for="l in i.how" :key="l" :class="{ sum: /^[=+−]/.test(l) }">{{ fa(l) }}</span></div>
          <div v-if="owner && i.kind === 'count'" class="btn-row">
            <button v-if="sure !== i.count_id" class="btn sm" @click="sure = i.count_id">اصلاح موجودی با این شمارش</button>
            <template v-else><span class="small">موجودی فایل انبار به عدد شمارش تغییر کند؟ این کار با نام شما ثبت می‌شود.</span>
              <button class="btn primary sm" :disabled="applying === i.count_id" @click="apply(i)">بله، اصلاح شود</button>
              <button class="btn ghost sm" @click="sure = 0">نه</button></template>
          </div>
        </article>
      </section>
      <section v-else class="card rc-clear"><Icon name="shield" :size="22" /><b>مغایرتی نیست.</b><span class="muted">همه‌ی بررسی‌ها جور است.</span></section>
    </template>
    <EventFeed v-if="events" full @changed="changed" />
  </div>
</template>
