<script setup>
// Placeholders in the shape of the content that is on its way, so nothing jumps when it arrives.
// kind: text (lines), stat (number card), row (list row with an icon or avatar), letter (letter card),
//       gauge (attendance ring), chart (bars), field (form label and input), chips (a row of pills)
// count: how many of the block; lines: lines for text; round: a round avatar instead of a square icon
defineProps({
  kind: { default: "text" }, count: { default: 1 }, lines: { default: 3 }, round: { type: Boolean, default: false },
})
const BAR_HEIGHTS = [62, 78, 54, 88, 70, 92, 60, 84, 74, 66]
</script>

<template>
  <div :class="['sk-wrap', 'sk-k-' + kind]" aria-hidden="true">
    <template v-for="i in count" :key="i">
      <div v-if="kind === 'text'" class="sk-lines">
        <span v-for="l in lines" :key="l" class="sk" :style="{ width: l === lines && lines > 1 ? '58%' : (l % 2 ? '100%' : '92%') }"></span>
      </div>

      <div v-else-if="kind === 'stat'" class="card stat sk-card">
        <div class="stat-top"><span class="sk sk-icon lg"></span><span class="sk" style="width: 44px; height: 26px"></span></div>
        <span class="sk" style="width: 62%"></span><span class="sk sm" style="width: 44%"></span>
      </div>

      <div v-else-if="kind === 'row'" class="sk-row">
        <span :class="['sk', 'sk-icon', { round }]"></span>
        <div class="sk-lines grow"><span class="sk" :style="{ width: (i % 2 ? 64 : 52) + '%' }"></span><span class="sk sm" :style="{ width: (i % 2 ? 82 : 70) + '%' }"></span></div>
        <span class="sk sk-pill"></span>
      </div>

      <div v-else-if="kind === 'letter'" class="card sk-card sk-letter">
        <div class="sk-between"><span class="sk" style="width: 46%; height: 15px"></span><span class="sk sk-pill"></span></div>
        <span class="sk sm" style="width: 32%"></span>
        <div class="sk-chips"><span class="sk sk-pill"></span><span class="sk sk-pill"></span></div>
        <span class="sk" style="width: 88%"></span>
        <span class="sk sk-box"></span>
        <div class="sk-chips"><span class="sk sk-btn"></span><span class="sk sk-btn"></span></div>
      </div>

      <div v-else-if="kind === 'gauge'" class="sk-gauge">
        <span class="sk sk-ring"></span>
        <div class="sk-three"><span v-for="n in 3" :key="n"><i class="sk" style="width: 28px; height: 18px"></i><i class="sk sm" style="width: 40px"></i></span></div>
      </div>

      <div v-else-if="kind === 'chart'" class="sk-chart">
        <span v-for="(h, n) in BAR_HEIGHTS" :key="n" class="sk" :style="{ height: h + '%' }"></span>
      </div>

      <div v-else-if="kind === 'field'" class="sk-field"><span class="sk sm" style="width: 30%"></span><span class="sk sk-input"></span></div>

      <div v-else-if="kind === 'chips'" class="sk-chips"><span v-for="n in 3" :key="n" class="sk sk-pill" :style="{ width: (70 + n * 18) + 'px' }"></span></div>
    </template>
  </div>
</template>
