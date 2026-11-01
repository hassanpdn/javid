<script setup>
// The dark moving background of the live site's first pages (the door and the list of assistants):
// slow colour clouds, a faint grid that fades out at the edges, and a few twinkling dots.
// The clouds are soft radial gradients, not blurred circles: a blur filter on such big moving shapes (with a blend
// mode) needs huge graphics buffers on phones' dense screens, and iPhone Safari killed the page for it.
</script>

<template>
  <div class="a-sky" aria-hidden="true">
    <span class="a-blob b1"></span><span class="a-blob b2"></span><span class="a-blob b3"></span><span class="a-blob b4"></span>
    <span class="a-grid"></span>
    <span v-for="n in 18" :key="n" class="a-star" :style="{ '--x': (n * 53) % 100 + '%', '--y': (n * 37) % 100 + '%', '--d': (n % 6) + 's' }"></span>
  </div>
</template>

<style scoped>
.a-sky { position: fixed; inset: 0; z-index: -1; pointer-events: none; overflow: hidden;
  background: radial-gradient(120% 80% at 50% 0%, #1d1b4b 0%, #0d0c24 55%, #07061a 100%); }
.a-blob { position: absolute; width: 56vmax; height: 56vmax; border-radius: 50%; opacity: .55;
  background: radial-gradient(closest-side, var(--c), transparent); will-change: transform; }
.b1 { --c: #7367f0; top: -18vmax; right: -14vmax; animation: a-float1 18s ease-in-out infinite alternate; }
.b2 { --c: #00bad1; bottom: -22vmax; left: -16vmax; opacity: .42; animation: a-float2 22s ease-in-out infinite alternate; }
.b3 { --c: #ff6fa8; top: 26%; left: 50%; width: 38vmax; height: 38vmax; opacity: .3; animation: a-float3 26s ease-in-out infinite alternate; }
.b4 { --c: #ffb057; bottom: 4%; right: 26%; width: 28vmax; height: 28vmax; opacity: .22; animation: a-float1 30s ease-in-out infinite alternate-reverse; }
.a-grid { position: absolute; inset: 0; opacity: .5;
  background-image: linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px);
  background-size: 48px 48px; mask-image: radial-gradient(70% 60% at 50% 45%, #000 20%, transparent 75%); }
.a-star { position: absolute; left: var(--x); top: var(--y); width: 3px; height: 3px; border-radius: 50%; background: #fff;
  box-shadow: 0 0 8px 2px rgba(255,255,255,.5); opacity: 0; animation: a-twinkle 6s ease-in-out var(--d) infinite; }
@keyframes a-float1 { to { transform: translate(-8vmax, 10vmax) scale(1.12); } }
@keyframes a-float2 { to { transform: translate(10vmax, -8vmax) scale(1.08); } }
@keyframes a-float3 { to { transform: translate(-18vmax, 6vmax) scale(.9); } }
@keyframes a-twinkle { 0%, 100% { opacity: 0; transform: scale(.6); } 50% { opacity: .9; transform: scale(1); } }
@media (prefers-reduced-motion: reduce) { .a-blob, .a-star { animation: none; } .a-star { opacity: .5; } }
</style>
