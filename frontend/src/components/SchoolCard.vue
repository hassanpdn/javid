<script setup>
// The school's "ID card" next to the setup form. It fills in as the steps are completed:
// a finished step shows solid with a check, the step being filled shows faded, later steps show placeholders.
// It tilts towards the mouse, and plays the build checklist and the success burst at the end.
import { ref, computed, onMounted, onUnmounted } from "vue"
import { gsap, motion } from "../lib/motion.js"
import Icon from "./Icon.vue"

const props = defineProps({
  form: Object,            // the setup form's values
  done: Object,            // Set of finished step indexes
  step: Number,            // the step being filled
  building: Array,         // build checklist: [{ text, done }] while the demo is being built, else null
  success: Boolean,
})
const card = ref(null), shine = ref(null), burst = ref(null)

const schoolName = computed(() => (props.form.name || "").replace(/^دبستان\s*/, "").trim())
const state = (i) => props.done.has(i) ? "done" : props.step === i ? "live" : "todo"
const people = computed(() => [
  { role: "مدیر مدرسه", title: props.form.manager_title, name: props.form.manager_name, tone: "primary" },
  { role: "مشاور", title: props.form.counselor_title, name: props.form.counselor_name, tone: "success" },
  { role: "کارمند اداری", title: props.form.staff_title, name: props.form.staff_name, tone: "info" },
])
const progress = computed(() => props.done.size)

// 3D tilt: the card leans towards the mouse and a soft light follows it
let rx, ry, sx
function onMove(e) {
  if (!rx) return
  const r = card.value.getBoundingClientRect()
  const x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5
  ry(x * 14); rx(-y * 10); sx(x * 100)
}
function onLeave() { if (rx) { rx(0); ry(0); sx(0) } }

// colored particles flying out of the card when the demo is ready
function celebrate() {
  if (!motion || !burst.value) return
  const colors = ["var(--primary)", "var(--info)", "var(--success)", "var(--warning)", "var(--danger)"]
  for (let i = 0; i < 36; i++) {
    const p = document.createElement("i")
    p.style.background = colors[i % colors.length]
    burst.value.appendChild(p)
    const angle = Math.random() * Math.PI * 2, dist = 120 + Math.random() * 180
    gsap.fromTo(p, { x: 0, y: 0, scale: 1, opacity: 1 },
      { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist - 40, scale: 0, rotation: Math.random() * 360,
        duration: 1 + Math.random() * .6, ease: "power3.out", onComplete: () => p.remove() })
  }
  gsap.fromTo(card.value, { scale: 1 }, { scale: 1.04, duration: .25, yoyo: true, repeat: 1, ease: "power2.out" })
}
defineExpose({ celebrate })

onMounted(() => {
  if (!motion) return
  gsap.set(card.value, { transformPerspective: 900 })
  rx = gsap.quickTo(card.value, "rotationX", { duration: .6, ease: "power3.out" })
  ry = gsap.quickTo(card.value, "rotationY", { duration: .6, ease: "power3.out" })
  sx = gsap.quickTo(shine.value, "xPercent", { duration: .8, ease: "power3.out" })
  gsap.from(card.value, { y: 40, opacity: 0, rotationY: -20, duration: .9, ease: "power3.out", delay: .2 })
})
onUnmounted(() => { if (card.value) gsap.killTweensOf(card.value) })
</script>

<template>
  <div class="school-card-wrap" @mousemove="onMove" @mouseleave="onLeave">
    <div ref="card" :class="['school-card', { ready: progress >= 3, success }]" aria-live="polite">
      <span ref="shine" class="sc-shine" aria-hidden="true"></span>
      <header class="sc-head">
        <i class="sc-circle a"></i><i class="sc-circle b"></i>
        <span class="sc-logo">{{ (schoolName || "؟")[0] }}</span>
        <div class="sc-title">
          <small>کارت مدرسه · با هر مرحله پر می‌شود</small>
          <b :class="{ ghost: !schoolName }">{{ schoolName ? "دبستان " + schoolName : "نام مدرسه" }}</b>
          <span v-if="form.gender" class="sc-badge">{{ form.gender === "boys" ? "پسرانه" : "دخترانه" }}</span>
        </div>
      </header>

      <div class="sc-body">
        <section :class="['sc-row', state(1)]">
          <span class="tint sm t-warning"><Icon name="mapPin" :size="18" /></span>
          <div v-if="state(1) !== 'todo'" class="sc-text">
            <small>آموزش و پرورش</small>
            <b>{{ [form.district, form.city].filter(Boolean).join("، ") || "..." }}</b>
          </div>
          <div v-else class="sc-skeleton"><i></i><i style="width: 55%"></i></div>
          <Icon v-if="state(1) === 'done'" name="check" :size="18" class="sc-check" />
        </section>

        <section v-for="(p, i) in people" :key="p.role" :class="['sc-row', state(2)]">
          <span :class="['sc-avatar', 't-' + p.tone]">{{ (p.name || p.role)[0] }}</span>
          <div v-if="state(2) !== 'todo'" class="sc-text">
            <small>{{ p.role }}</small>
            <b>{{ [p.title, p.name].filter(Boolean).join(" ") || "..." }}</b>
          </div>
          <div v-else class="sc-skeleton"><i style="width: 40%"></i><i style="width: 70%"></i></div>
          <Icon v-if="state(2) === 'done'" name="check" :size="18" class="sc-check" />
        </section>

        <footer class="sc-foot">
          <div class="sc-progress"><span :style="{ width: progress / 3 * 100 + '%' }"></span></div>
          <small>{{ progress >= 3 ? "آماده ساخت دمو" : `${["۰", "۱", "۲"][progress]} از ۳ مرحله` }}</small>
        </footer>
      </div>

      <div v-if="building" class="sc-build">
        <div class="sc-build-head"><Icon :name="success ? 'check' : 'sparkles'" :size="22" />
          <b>{{ success ? "دمو آماده است" : "در حال ساخت دمو..." }}</b></div>
        <ul>
          <li v-for="item in building" :key="item.text" :class="{ done: item.done }">
            <span class="sc-tick"><Icon v-if="item.done" name="check" :size="14" /></span>{{ item.text }}
          </li>
        </ul>
      </div>
      <div ref="burst" class="sc-burst" aria-hidden="true"></div>
    </div>
  </div>
</template>
