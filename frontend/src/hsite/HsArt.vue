<script setup>
// Drawn pictures of the hotel (drawings, not photos whose rights are unknown, as on the eco-lodge's website): «hero»
// for the top of the page (the hotel on the shore at sunset) and one scene per room type. Plain SVG; the waves move
// with a CSS animation only.
defineProps({ kind: { type: String, default: "hero" } })
</script>

<template>
  <svg viewBox="0 0 400 260" class="eco-art hs-art" role="img" aria-hidden="true" preserveAspectRatio="xMidYMid slice">
    <defs>
      <linearGradient id="hs-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1f3b5c" /><stop offset=".55" stop-color="#d98b6a" /><stop offset="1" stop-color="#f3c98b" /></linearGradient>
      <linearGradient id="hs-day" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a9d3e8" /><stop offset="1" stop-color="#eaf4f6" /></linearGradient>
      <linearGradient id="hs-sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f6f8f" /><stop offset="1" stop-color="#1c4a66" /></linearGradient>
      <linearGradient id="hs-wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f7f2e8" /><stop offset="1" stop-color="#e6dccb" /></linearGradient>
    </defs>

    <template v-if="kind === 'hero'">
      <rect width="400" height="260" fill="url(#hs-sky)" />
      <circle cx="300" cy="150" r="30" fill="#f8d49a" opacity=".95" />
      <path d="M40 120 Q120 70 200 110 T380 100 V160 H40Z" fill="#3f5f4a" opacity=".55" />
      <rect y="160" width="400" height="100" fill="url(#hs-sea)" />
      <g class="hs-waves"><path d="M0 178 q20 -6 40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0" stroke="#f8d49a" stroke-width="2" fill="none" opacity=".6" />
        <path d="M0 200 q20 -6 40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0 t40 0" stroke="#cfe6ef" stroke-width="2" fill="none" opacity=".35" /></g>
      <path d="M0 232 Q200 214 400 236 V260 H0Z" fill="#e9d3a6" />
      <g transform="translate(22 128) scale(.62)"><rect x="0" y="0" width="150" height="128" rx="4" fill="url(#hs-wall)" />
      <g fill="#2f6f8f" opacity=".85"><rect v-for="i in 15" :key="i" :x="12 + ((i - 1) % 5) * 27" :y="12 + Math.floor((i - 1) / 5) * 34" width="17" height="22" rx="2" /></g>
      <g stroke="#b8a888" stroke-width="2"><line v-for="r in 3" :key="r" x1="6" :x2="144" :y1="36 + (r - 1) * 34" :y2="36 + (r - 1) * 34" /></g>
      <rect x="58" y="104" width="34" height="24" fill="#8a6a45" /></g>
      <g fill="#2e4a35"><path d="M240 232 q-2 -40 4 -70" stroke="#6b4e2e" stroke-width="4" fill="none" /><ellipse cx="244" cy="160" rx="22" ry="7" transform="rotate(-20 244 160)" /><ellipse cx="246" cy="160" rx="22" ry="7" transform="rotate(25 246 160)" />
        <path d="M30 232 q2 -34 -4 -60" stroke="#6b4e2e" stroke-width="4" fill="none" /><ellipse cx="26" cy="172" rx="18" ry="6" transform="rotate(-25 26 172)" /><ellipse cx="28" cy="172" rx="18" ry="6" transform="rotate(20 28 172)" /></g>
    </template>

    <template v-else>
      <rect width="400" height="260" fill="#f3ede2" />
      <!-- the window: sea, or the garden -->
      <rect x="150" y="34" width="210" height="140" rx="6" :fill="kind === 'dbl_garden' ? '#cfe3c6' : 'url(#hs-day)'" />
      <template v-if="kind === 'dbl_garden'">
        <g fill="#5f8a55"><circle cx="190" cy="140" r="34" /><circle cx="250" cy="130" r="40" /><circle cx="320" cy="142" r="30" /></g>
        <g fill="#f0a63a"><circle cx="240" cy="118" r="4" /><circle cx="262" cy="134" r="4" /><circle cx="186" cy="132" r="3.5" /><circle cx="318" cy="136" r="3.5" /></g>
      </template>
      <template v-else>
        <rect x="150" y="110" width="210" height="64" fill="url(#hs-sea)" />
        <path d="M150 130 q15 -5 30 0 t30 0 t30 0 t30 0 t30 0 t30 0 t30 0" stroke="#cfe6ef" stroke-width="2" fill="none" opacity=".6" />
        <path v-if="kind === 'villa'" d="M150 160 Q255 150 360 164 V174 H150Z" fill="#e9d3a6" />
      </template>
      <line x1="255" y1="34" x2="255" y2="174" stroke="#fff" stroke-width="5" />
      <rect x="150" y="34" width="210" height="140" rx="6" fill="none" stroke="#fff" stroke-width="7" />
      <!-- a balcony rail for the sea-view rooms and the suite -->
      <g v-if="kind === 'dbl_sea' || kind === 'suite'" stroke="#8a7a62" stroke-width="2.5"><line x1="150" y1="150" x2="360" y2="150" /><line v-for="i in 10" :key="i" :x1="150 + i * 21" :x2="150 + i * 21" y1="150" y2="174" /></g>
      <rect y="206" width="400" height="54" fill="#d9c7a7" />
      <!-- the room: beds, or a sofa for the suite and the villa -->
      <template v-if="kind === 'suite' || kind === 'villa'">
        <rect x="24" y="160" width="140" height="50" rx="12" fill="#3f6f8a" /><rect x="24" y="146" width="140" height="26" rx="12" fill="#4f7f9a" />
        <rect x="190" y="186" width="80" height="12" rx="4" fill="#8a6a45" /><circle cx="230" cy="180" r="7" fill="#e8a85a" />
      </template>
      <template v-else>
        <g v-for="i in (kind === 'triple' ? 3 : 2)" :key="i">
          <rect :x="10 + (i - 1) * (kind === 'triple' ? 92 : 120)" y="168" :width="kind === 'triple' ? 82 : 110" height="40" rx="6" fill="#fff" stroke="#d6cab5" />
          <rect :x="10 + (i - 1) * (kind === 'triple' ? 92 : 120)" y="160" :width="kind === 'triple' ? 82 : 110" height="14" rx="5" fill="#2f6f8f" />
          <rect :x="18 + (i - 1) * (kind === 'triple' ? 92 : 120)" y="172" width="26" height="12" rx="4" fill="#efe6d6" />
        </g>
      </template>
      <circle cx="120" cy="70" r="16" fill="#f2d39b" /><rect x="116" y="84" width="8" height="40" fill="#8a7a62" />
    </template>
  </svg>
</template>
