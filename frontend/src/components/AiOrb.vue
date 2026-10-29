<script setup>
// The assistant's animated "orb". busy makes its outer ring spin faster while the model is working.
// Each moving part is its own small svg in its own box, stacked on the others, and the boxes turn or breathe with
// CSS: the graphics card moves a whole box on its own (it does not do that for parts inside an svg, or for an svg
// element itself). Endless GSAP tweens on the svg's parts made the browser redo the page's styles and layout on every
// frame, all the time, and the first-visit guide stuttered over it.
defineProps({ size: { default: 120 }, busy: { default: false } })
</script>

<template>
  <span :class="['orb', { busy }]" :style="{ width: size + 'px', height: size + 'px' }" aria-hidden="true">
    <i class="o-halo"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="56" style="fill: var(--primary)" /></svg></i>
    <i class="o-ring"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="50" fill="none" style="stroke: var(--primary)" stroke-opacity=".4" stroke-width="1.5" stroke-dasharray="4 7" /></svg></i>
    <i class="o-core"><svg viewBox="0 0 120 120">
      <defs><linearGradient id="orbGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color: var(--primary)" /><stop offset="1" style="stop-color: var(--info)" /></linearGradient></defs>
      <circle cx="60" cy="60" r="34" fill="url(#orbGrad)" />
      <path d="M60 42c1.6 8.8 5.2 12.4 14 14-8.8 1.6-12.4 5.2-14 14-1.6-8.8-5.2-12.4-14-14 8.8-1.6 12.4-5.2 14-14Z" fill="#fff" />
      <path d="M74 38c.6 3.4 2 4.8 5.4 5.4-3.4.6-4.8 2-5.4 5.4-.6-3.4-2-4.8-5.4-5.4 3.4-.6 4.8-2 5.4-5.4Z" fill="#fff" opacity=".8" />
    </svg></i>
    <i class="o-sat a"><svg viewBox="0 0 120 120"><circle cx="60" cy="10" r="4" style="fill: var(--warning)" /></svg></i>
    <i class="o-sat b"><svg viewBox="0 0 120 120"><circle cx="110" cy="60" r="3" style="fill: var(--success)" /></svg></i>
  </span>
</template>

<style scoped>
/* o- names: plain ones like «ring» are also Tailwind utilities (a ring is a 1px frame) */
.orb { position: relative; display: block; flex: none; }
.orb i { position: absolute; inset: 0; }
.orb svg { display: block; width: 100%; height: 100%; overflow: visible; }
.o-halo { opacity: .08; }
@media (prefers-reduced-motion: no-preference) {
  .o-ring { animation: orb-turn 18s linear infinite; }
  .busy .o-ring { animation-duration: 2.25s; }
  .o-sat.a { animation: orb-turn 9s linear infinite; }
  .o-sat.b { animation: orb-turn 13s linear infinite reverse; }
  .o-core { animation: orb-breathe 1.8s ease-in-out infinite alternate; }
  .o-halo { animation: orb-halo 2.2s ease-in-out infinite alternate; }
}
@keyframes orb-turn { to { rotate: 360deg; } }
@keyframes orb-breathe { to { scale: 1.06; } }
@keyframes orb-halo { to { scale: 1.1; opacity: .18; } }
</style>
