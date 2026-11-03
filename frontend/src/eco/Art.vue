<script setup>
// Drawn pictures of the eco-lodge (Hassan's choice: drawings, not photos from the internet whose rights are unknown).
// One scene per kind of unit, and «hero» for the website's top: a mud-brick village with domes and windcatchers,
// dunes, and a night sky. Plain SVG in the lodge's earthy colours; the stars twinkle with a CSS animation only.
// Each kind now has a generated photo (public/photos, made with Google Flow for the demo, Hassan's choice); the
// drawing stays for a kind without one. «yard» is the courtyard beside the lodge's story. A host's own uploaded
// photos still come first wherever a unit is shown.
defineProps({ kind: { type: String, default: "dome" }, night: { type: Boolean, default: false } })
const PHOTOS = { hero: "eco-hero", yard: "eco-court", dome: "eco-dome", court: "eco-porch", family: "eco-family", tower: "eco-tower", roof: "eco-roof", garden: "eco-garden" }
const STARS = [[40, 30], [90, 52], [150, 22], [210, 44], [262, 18], [318, 40], [360, 26], [120, 70], [300, 66], [190, 76], [70, 84], [340, 88]]
</script>

<template>
  <img v-if="PHOTOS[kind]" :src="`/photos/${PHOTOS[kind]}.webp`" alt="" class="eco-art eco-photo" :class="'eco-photo-' + kind" :loading="kind === 'hero' ? 'eager' : 'lazy'" decoding="async">
  <svg v-else viewBox="0 0 400 260" class="eco-art" :class="{ night: night || kind === 'roof' || kind === 'hero' }" role="img" aria-hidden="true" preserveAspectRatio="xMidYMid slice">
    <defs>
      <linearGradient id="eco-day" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f6d7a7" /><stop offset="1" stop-color="#fbeedb" /></linearGradient>
      <linearGradient id="eco-night" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d2346" /><stop offset=".7" stop-color="#3b3a6b" /><stop offset="1" stop-color="#8c5e6e" /></linearGradient>
      <linearGradient id="eco-wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d9a873" /><stop offset="1" stop-color="#c28a55" /></linearGradient>
      <linearGradient id="eco-sand" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e8bf86" /><stop offset="1" stop-color="#d6a066" /></linearGradient>
    </defs>
    <rect width="400" height="260" :fill="night || kind === 'roof' || kind === 'hero' ? 'url(#eco-night)' : 'url(#eco-day)'" />
    <g v-if="night || kind === 'roof' || kind === 'hero'" class="eco-stars">
      <circle v-for="(s, i) in STARS" :key="i" :cx="s[0]" :cy="s[1]" :r="i % 3 ? 1.4 : 2.2" fill="#fff8e6" :style="{ animationDelay: (i * .37) + 's' }" />
      <circle cx="330" cy="46" r="16" fill="#fdf1c7" /><circle cx="337" cy="41" r="14" fill="#2a2d55" />
    </g>
    <circle v-else cx="320" cy="60" r="26" fill="#f2b45a" opacity=".9" />

    <!-- dunes -->
    <path d="M0 200 Q80 160 170 190 T400 180 V260 H0Z" fill="url(#eco-sand)" />
    <path d="M0 225 Q120 200 230 222 T400 215 V260 H0Z" fill="#c98f58" opacity=".55" />

    <g v-if="kind === 'hero'">
      <rect x="40" y="150" width="70" height="55" fill="url(#eco-wall)" /><path d="M40 150 Q75 110 110 150Z" fill="#cf9a62" />
      <rect x="120" y="135" width="26" height="70" fill="url(#eco-wall)" /><rect x="116" y="128" width="34" height="10" fill="#b77d48" />
      <rect x="124" y="140" width="5" height="16" fill="#5b3a22" /><rect x="137" y="140" width="5" height="16" fill="#5b3a22" />
      <rect x="155" y="160" width="110" height="45" fill="url(#eco-wall)" />
      <path d="M160 160 Q182 128 204 160Z" fill="#cf9a62" /><path d="M210 160 Q235 122 260 160Z" fill="#cf9a62" />
      <path d="M200 205 V186 Q210 172 220 186 V205Z" fill="#5b3a22" />
      <rect x="280" y="145" width="80" height="60" fill="url(#eco-wall)" /><path d="M285 145 Q320 108 355 145Z" fill="#cf9a62" />
      <rect x="300" y="168" width="10" height="12" rx="5" fill="#ffd48a" /><rect x="330" y="168" width="10" height="12" rx="5" fill="#ffd48a" />
      <rect x="70" y="172" width="10" height="12" rx="5" fill="#ffd48a" />
    </g>
    <g v-else-if="kind === 'dome'">
      <rect x="110" y="140" width="180" height="70" fill="url(#eco-wall)" />
      <path d="M125 140 Q200 60 275 140Z" fill="#cf9a62" />
      <path d="M185 210 V178 Q200 160 215 178 V210Z" fill="#5b3a22" />
      <circle cx="200" cy="112" r="7" fill="#7a4c2b" /><rect x="140" y="165" width="16" height="20" rx="8" fill="#7a4c2b" /><rect x="244" y="165" width="16" height="20" rx="8" fill="#7a4c2b" />
    </g>
    <g v-else-if="kind === 'court'">
      <rect x="60" y="120" width="280" height="90" fill="url(#eco-wall)" />
      <path v-for="x in [80, 145, 210, 275]" :key="x" :d="`M${x} 210 V160 Q${x + 22} 132 ${x + 44} 160 V210Z`" fill="#8a5a36" />
      <ellipse cx="200" cy="222" rx="70" ry="10" fill="#5fa3b5" opacity=".8" />
      <rect x="318" y="150" width="6" height="60" fill="#6b4226" /><circle cx="321" cy="140" r="22" fill="#5c8a4a" />
      <circle cx="314" cy="146" r="4" fill="#c0392b" /><circle cx="328" cy="134" r="4" fill="#c0392b" />
    </g>
    <g v-else-if="kind === 'family'">
      <rect x="70" y="140" width="130" height="70" fill="url(#eco-wall)" /><path d="M80 140 Q135 90 190 140Z" fill="#cf9a62" />
      <rect x="200" y="125" width="130" height="85" fill="url(#eco-wall)" /><path d="M210 125 Q265 70 320 125Z" fill="#cf9a62" />
      <path d="M125 210 V180 Q135 168 145 180 V210Z" fill="#5b3a22" /><path d="M255 210 V172 Q265 158 275 172 V210Z" fill="#5b3a22" />
      <rect x="225" y="150" width="14" height="16" rx="7" fill="#7a4c2b" /><rect x="292" y="150" width="14" height="16" rx="7" fill="#7a4c2b" />
    </g>
    <g v-else-if="kind === 'tower'">
      <rect x="150" y="160" width="140" height="50" fill="url(#eco-wall)" />
      <rect x="175" y="70" width="44" height="140" fill="url(#eco-wall)" /><rect x="168" y="60" width="58" height="14" fill="#b77d48" />
      <rect v-for="x in [181, 192, 203]" :key="x" :x="x" y="80" width="6" height="34" fill="#5b3a22" />
      <path d="M245 210 V185 Q255 174 265 185 V210Z" fill="#5b3a22" />
    </g>
    <g v-else-if="kind === 'garden'">
      <rect x="150" y="140" width="130" height="70" fill="url(#eco-wall)" /><path d="M160 140 Q215 92 270 140Z" fill="#cf9a62" />
      <path d="M205 210 V182 Q215 170 225 182 V210Z" fill="#5b3a22" />
      <g v-for="x in [60, 105, 310, 350]" :key="x"><rect :x="x - 3" y="170" width="6" height="40" fill="#6b4226" /><circle :cx="x" cy="160" r="20" fill="#6e9a4f" /><circle :cx="x - 8" cy="154" r="3" fill="#d8c05a" /></g>
    </g>
    <g v-else-if="kind === 'roof'">
      <rect x="60" y="170" width="280" height="40" fill="url(#eco-wall)" />
      <rect x="140" y="150" width="120" height="16" rx="4" fill="#efe3cf" /><rect x="140" y="146" width="34" height="10" rx="4" fill="#fff" />
      <rect x="146" y="166" width="5" height="10" fill="#6b4226" /><rect x="250" y="166" width="5" height="10" fill="#6b4226" />
      <path d="M140 156 H260 V166 H140Z" fill="#b5524a" opacity=".85" />
    </g>
  </svg>
</template>

<style>
.eco-art { display: block; width: 100%; height: 100%; }
.eco-stars circle { animation: eco-twinkle 3.2s ease-in-out infinite; }
@keyframes eco-twinkle { 0%, 100% { opacity: 1 } 50% { opacity: .35 } }
@media (prefers-reduced-motion: reduce) { .eco-stars circle { animation: none; } }
</style>
