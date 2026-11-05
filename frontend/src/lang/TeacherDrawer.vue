<script setup>
// One teacher, or a new one: the levels they teach (chips to switch), the hours they come (a grid to tap, manager
// only), and their classes this term and next. Changing hours does not move a class: the timetable then shows any class
// left at an hour the teacher no longer comes.
import { ref, reactive, computed } from "vue"
import { api, fa, langSession } from "../lib/api.js"
import { toast } from "../lib/notify.js"
import { instInfo, short } from "./lib.js"
import Icon from "../components/Icon.vue"

const props = defineProps({ teacher: Object })
const emit = defineEmits(["close", "saved", "open"])
const owner = langSession.user.role === "owner"
const isNew = computed(() => !!props.teacher.new)
const f = reactive({ name: "", phone: "", levels: [...(props.teacher.levels || [])], avail: JSON.parse(JSON.stringify(props.teacher.avail || {})) })
const busy = ref(false)
const flipLevel = (k) => { if (!owner) return; f.levels = f.levels.includes(k) ? f.levels.filter((x) => x !== k) : [...f.levels, k] }
const has = (p, s) => (f.avail[p] || []).includes(s)
const flip = (p, s) => { if (!owner) return; f.avail[p] = has(p, s) ? f.avail[p].filter((x) => x !== s) : [...(f.avail[p] || []), s] }
async function save() {
  busy.value = true
  try {
    if (isNew.value) await api("/lang/teachers", { name: f.name, phone: f.phone, levels: f.levels })
    else await api(`/lang/teachers/${props.teacher.id}`, { levels: f.levels, avail: f.avail })
    toast({ tone: "success", title: isNew.value ? "استاد جدید اضافه شد" : "ذخیره شد" }); emit("saved"); if (isNew.value) emit("close")
  } catch (e) { toast({ tone: "danger", title: typeof e.message === "string" && e.message.startsWith("[") ? "نام، شماره و دست‌کم یک سطح را بنویسید" : e.message }) }
  finally { busy.value = false }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <aside class="drawer k-drawer" v-drawer :aria-label="isNew ? 'استاد جدید' : teacher.name">
      <div class="drawer-head"><b class="text-ink">{{ isNew ? "استاد جدید" : teacher.name }}</b><button class="icon-btn" @click="emit('close')" aria-label="بستن"><Icon name="x" /></button></div>
      <div class="drawer-body" tabindex="0">
        <section v-if="isNew" class="card flex flex-col gap-2">
          <label class="field"><span>نام و نام خانوادگی</span><input v-model="f.name" maxlength="60"></label>
          <label class="field"><span>شماره‌ی همراه</span><input v-model="f.phone" inputmode="tel" dir="ltr" placeholder="09121234567"></label>
          <small class="muted">ساعت‌های آمدن، اول همه‌ی عصرها است؛ پس از ثبت می‌توانید عوضش کنید.</small>
        </section>
        <section v-else class="card k-head">
          <span class="k-meta" dir="ltr" style="text-align: right">{{ fa(teacher.phone) }}</span>
          <span class="k-meta">از {{ fa(teacher.joined_text) }} · این ترم {{ fa(teacher.hours.current) }} ساعت در هفته، ترم بعد {{ fa(teacher.hours.next) }} ساعت</span>
        </section>

        <section class="card">
          <div class="card-head">سطح‌هایی که درس می‌دهد</div>
          <div class="lg-levels"><button v-for="l in instInfo.levels" :key="l.key" type="button" :class="['lg-chip', 'lg-lv', 'lv-' + l.key, { off: !f.levels.includes(l.key) }]" :aria-pressed="f.levels.includes(l.key)" :disabled="!owner" @click="flipLevel(l.key)">{{ l.fa }} · {{ l.cefr }}</button></div>
        </section>

        <section v-if="!isNew" class="card">
          <div class="card-head">ساعت‌هایی که می‌آید</div>
          <div class="lg-avail-edit">
            <span></span><small v-for="s in instInfo.slots" :key="s">{{ fa(s) }}</small>
            <template v-for="(name, p) in instInfo.pairs" :key="p"><span>{{ name }}</span>
              <button v-for="s in instInfo.slots" :key="s" type="button" :class="{ on: has(p, s) }" :aria-pressed="has(p, s)" :aria-label="`${name} ساعت ${s}`" :disabled="!owner" @click="flip(p, s)"><Icon name="check" :size="14" /></button></template>
          </div>
        </section>

        <div v-if="owner" class="btn-row"><button class="btn primary" :disabled="busy || !f.levels.length || (isNew && (f.name.trim().length < 3 || f.phone.trim().length < 10))" @click="save"><Icon name="check" :size="16" />{{ isNew ? "افزودن استاد" : "ذخیره" }}</button></div>

        <template v-if="!isNew"><section v-for="(list, k) in teacher.classes" :key="k" class="card">
          <div class="card-head">{{ k === 'current' ? 'کلاس‌های این ترم' : 'کلاس‌های ترم بعد' }} <span class="count">{{ fa(list.length) }}</span></div>
          <p v-if="!list.length" class="muted small">کلاسی ندارد.</p>
          <ul class="k-mini"><li v-for="c in list" :key="c.id"><button class="link" style="text-align: right" @click="emit('open', c.id)">{{ c.course_name }} <span :class="['lg-chip', 'lg-lv', 'lv-' + c.level]">{{ short(c.course) }}</span></button>
            <small class="muted">{{ c.pair_text }} ساعت {{ fa(c.time) }} · {{ fa(c.room_name) }} · {{ fa(c.seats) }} نفر</small></li></ul>
        </section></template>
      </div>
    </aside>
  </div>
</template>
