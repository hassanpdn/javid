<script setup>
// The dark moving background of the live site's first pages (the door and the list of assistants):
// slow colour clouds, a faint grid that fades out at the edges, and a few twinkling dots.
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
.a-blob { position: absolute; width: 46vmax; height: 46vmax; border-radius: 50%; filter: blur(70px); opacity: .5; mix-blend-mode: screen; }
.b1 { background: #7367f0; top: -14vmax; right: -10vmax; animation: a-float1 18s ease-in-out infinite alternate; }
.b2 { background: #00bad1; bottom: -18vmax; left: -12vmax; opacity: .38; animation: a-float2 22s ease-in-out infinite alternate; }
.b3 { background: #ff6fa8; top: 30%; left: 55%; width: 30vmax; height: 30vmax; opacity: .26; animation: a-float3 26s ease-in-out infinite alternate; }
.b4 { background: #ffb057; bottom: 8%; right: 30%; width: 20vmax; height: 20vmax; opacity: .18; animation: a-float1 30s ease-in-out infinite alternate-reverse; }
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
