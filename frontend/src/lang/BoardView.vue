<script setup>
// The timetable of a term: rooms across, the day's five slots down, one pair of days at a time. Every class is a card
// in its level's colour, with its seats. What does not work (a teacher or a room in two places, more learners than
// seats, a teacher at an hour they do not come, a class too small to open) is listed on top and marked red.
// Moving (manager only): pick a class, and every cell of every pair of days turns green where it can go, or says why
// not; a click on a green cell moves it, and the message for its learners is ready to send.
import { ref, computed, watch, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { instInfo, short } from "./lib.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import { defineAsyncComponent } from "vue"
const NewClassDialog = defineAsyncComponent(() => import("./NewClassDialog.vue"))

const props = defineProps({ start: { type: Object, default: () => ({ term: "current", pick: null }) }, canMove: Boolean })
const emit = defineEmits(["open", "message", "changed"])
const termKind = ref(props.start.term || "current"), d = ref(null), pair = ref("satmon")
const picked = ref(null), grid = ref(null), target = ref(null), busy = ref(false), making = ref(false)
const load = async () => { d.value = await api(`/lang/timetable?term=${termKind.value}`) }
onMounted(() => retryable(async () => {
  await load()
  const first = props.start.pick && d.value.classes.find((c) => c.id === props.start.pick)
  if (first) { pair.value = first.pair; if (props.canMove) pick(first) }
  else if (d.value.problems.length) pair.value = cls(d.value.problems[0].class_ids[0])?.pair || "satmon"
}))
watch(termKind, async () => { cancel(); d.value = null; await retryable(load) })

const cls = (id) => d.value?.classes.find((c) => c.id === id)
const bad = computed(() => new Set((d.value?.problems || []).flatMap((p) => p.class_ids)))
const badPairs = computed(() => new Set([...bad.value].map((id) => cls(id)?.pair)))
const rooms = computed(() => Object.entries(instInfo.rooms).map(([r, seats]) => ({ r: Number(r), seats })))
const at = (time, room) => (d.value?.classes || []).filter((c) => c.pair === pair.value && c.time === time && c.room === room)
const cell = (time, room) => grid.value?.find((g) => g.pair === pair.value && g.time === time && g.room === room)
const freeIn = (p) => grid.value ? grid.value.filter((g) => g.pair === p && g.ok && !g.here).length : 0

async function pick(c) {
  if (!props.canMove) { emit("open", c.id); return }
  if (picked.value?.id === c.id) { cancel(); return }
  picked.value = c; target.value = null; grid.value = null
  try { grid.value = await api(`/lang/classes/${c.id}/moves`) } catch (e) { toast({ tone: "danger", title: e.message }); cancel() }
}
const cancel = () => { picked.value = null; grid.value = null; target.value = null }
const show = (p) => { const c = cls(p.class_ids[p.class_ids.length - 1]); if (!c) return; pair.value = c.pair; if (props.canMove) pick(c); else emit("open", c.id) }
async function move() {
  busy.value = true
  try {
    const r = await api(`/lang/classes/${picked.value.id}/move`, { pair: target.value.pair, time: target.value.time, room: target.value.room })
    toast({ tone: "success", title: "کلاس جابه‌جا شد", body: `${r.class.course_name}: ${r.class.pair_text} ساعت ${fa(r.class.time)}، ${r.class.room_name}` })
    if (r.message) emit("message", { text: r.message, title: `پیام به ${fa(r.learners)} زبان‌آموز کلاس` })
    cancel(); await load(); emit("changed")
  } catch (e) { toast({ tone: "danger", title: e.message }) }
  finally { busy.value = false }
}
const PAIRS = computed(() => Object.entries(instInfo.pairs))
</script>

<template>
  <div>
    <div class="lg-board-tools">
      <div class="lg-seg" role="tablist" aria-label="ترم">
        <button role="tab" :aria-selected="termKind === 'current'" :class="{ on: termKind === 'current' }" @click="termKind = 'current'">این ترم</button>
        <button role="tab" :aria-selected="termKind === 'next'" :class="{ on: termKind === 'next' }" @click="termKind = 'next'">ترم بعد</button>
      </div>
      <span v-if="d" class="muted small grow">{{ fa(d.term.name) }} · از {{ fa(d.term.start_text) }} تا {{ fa(d.term.end_text) }} · {{ fa(d.classes.length) }} کلاس</span>
      <button v-if="canMove" class="btn sm" @click="making = true"><Icon name="plus" :size="16" />کلاس جدید</button>
    </div>
    <NewClassDialog v-if="making" :term="termKind" @close="making = false" @saved="async (c) => { making = false; await load(); pair = c.pair; emit('changed') }" />

    <Skeleton v-if="!d" kind="row" :count="6" />
    <template v-else>
      <div v-if="d.problems.length" class="lg-problems" data-tour="lg-problems">
        <div v-for="p in d.problems" :key="p.type + p.class_ids.join()" :class="['lg-problem', 'tone-' + p.tone]">
          <div><b>{{ fa(p.title) }}</b><small>{{ fa(p.detail) }}</small></div>
          <button class="btn sm" @click="show(p)"><Icon name="calendar" :size="14" />{{ canMove ? 'جابه‌جا کردن' : 'نشان بده' }}</button>
        </div>
      </div>
      <p v-else class="lg-next" style="margin-bottom: 14px"><Icon name="check" :size="18" /><span>در جدول این ترم تداخلی نیست: هیچ استاد و هیچ اتاقی در یک ساعت دو جا نیست.</span></p>

      <section class="card" data-tour="lg-grid">
        <div class="lg-seg" role="tablist" aria-label="روزها" style="margin-bottom: 14px; flex-wrap: wrap">
          <button v-for="[k, name] in PAIRS" :key="k" role="tab" :aria-selected="pair === k" :class="{ on: pair === k }" @click="pair = k">
            {{ name }}<i v-if="badPairs.has(k)" class="lg-red" aria-label="مشکل دارد"></i>
            <small v-if="grid" :style="{ opacity: .85 }">({{ fa(freeIn(k)) }} جای آزاد)</small></button>
        </div>
        <div class="lg-scroll">
          <div class="lg-grid">
            <span></span>
            <span v-for="r in rooms" :key="r.r" class="lg-gh"><b>کلاس {{ fa(r.r) }}</b>{{ fa(r.seats) }} جا</span>
            <template v-for="t in instInfo.slots" :key="t">
              <span class="lg-gt">{{ fa(t) }}<small>۹۰ دقیقه</small></span>
              <div v-for="r in rooms" :key="r.r" :class="['lg-cell', grid && !at(t, r.r).length ? (cell(t, r.r)?.ok ? 'ok' : 'no') : '']">
                <template v-if="at(t, r.r).length">
                  <div class="flex flex-col gap-1 grow" style="min-width: 0">
                    <button v-for="c in at(t, r.r)" :key="c.id" type="button"
                            :class="['lg-class', 'lg-lv', 'lv-' + c.level, { bad: bad.has(c.id), chosen: picked?.id === c.id, dim: picked && picked.id !== c.id }]"
                            :aria-label="`${c.course_name}، ${c.teacher}، ${c.seats} از ${c.capacity}`" @click="pick(c)">
                      <b>{{ c.course_name }} <span class="lg-chip">{{ short(c.course) }}</span></b>
                      <small>{{ c.teacher }}</small>
                      <span :class="['lg-seats', { over: c.seats > c.capacity }]"><span class="lg-bar"><i :style="{ width: Math.min(100, 100 * c.seats / c.capacity) + '%' }"></i></span>{{ fa(c.seats) }}/{{ fa(c.capacity) }}</span>
                    </button>
                  </div>
                </template>
                <template v-else-if="grid && cell(t, r.r)">
                  <button v-if="cell(t, r.r).ok" class="lg-cell-ok" @click="target = cell(t, r.r)" :aria-label="`انتقال به ساعت ${t}، کلاس ${r.r}`"><span><Icon name="plus" :size="16" /><br>این‌جا</span></button>
                  <span v-else class="lg-cell-why" :title="cell(t, r.r).why.join('؛ ')">{{ fa(cell(t, r.r).why[0]) }}</span>
                </template>
              </div>
            </template>
          </div>
        </div>
      </section>

      <div v-if="picked" class="lg-mover" role="status">
        <span v-if="!target">کلاس <b>{{ picked.course_name }}</b> ({{ picked.teacher }}) را کجا ببریم؟ خانه‌های سبز آزادند؛ روی هر خانه‌ی دیگر دلیلش نوشته شده است.<template v-if="grid && !freeIn(pair)"> در این روزها جای آزادی نیست؛ روزهای دیگر را ببینید.</template></span>
        <span v-else>{{ picked.course_name }} از {{ picked.pair_text }} ساعت {{ fa(picked.time) }}، {{ fa(picked.room_name) }} به <b>{{ instInfo.pairs[target.pair] }} ساعت {{ fa(target.time) }}، کلاس {{ fa(target.room) }}</b> برود؟</span>
        <button v-if="target" class="btn primary sm" :disabled="busy" @click="move"><Icon name="check" :size="16" />جابه‌جا کن</button>
        <button class="btn sm" @click="emit('open', picked.id)">پرونده‌ی کلاس</button>
        <button class="btn sm" @click="cancel">انصراف</button>
      </div>
    </template>
  </div>
</template>
