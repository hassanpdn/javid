<script setup>
// «معامله‌ها»: this month's deals and commission («از کجا؟» sums them), then every deal; a commission well under the
// agency's tariff is marked.
import { ref, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"
import HowTip from "../fabric/HowTip.vue"

const emit = defineEmits(["listing"])
const d = ref(null)
onMounted(() => retryable(async () => { d.value = await api("/estate/deals") }))
</script>

<template>
  <div class="flex flex-col gap-4">
    <div v-if="!d" class="card"><Skeleton kind="row" :count="6" /></div>
    <template v-else>
      <section class="card es-sum">
        <span class="tint lg t-success"><Icon name="check" :size="24" /></span>
        <div class="grow"><b>{{ fa(d.month.count) }} معامله در این ماه</b><small class="muted">کمیسیون {{ fa(d.month.fee_text) }}</small></div>
        <HowTip :lines="d.month.how" />
      </section>
      <ul class="es-list">
        <li v-for="x in d.items" :key="x.id" class="card es-visit">
          <div class="es-row-top"><b>{{ x.kind_text }} · {{ x.hood }}، {{ fa(x.area) }} متر</b><span class="muted small">{{ fa(x.date_text) }}</span></div>
          <div class="es-price">{{ fa(x.price_text) }}</div>
          <div class="es-meta">{{ x.buyer }} · {{ x.agents_text }}<template v-if="x.listing_id"> · <button class="link" @click="emit('listing', x.listing_id)">فایل {{ fa(x.listing_id) }}</button></template></div>
          <div class="es-tags"><span class="tag es-t-success">کمیسیون {{ fa(x.fee_text) }}</span><span v-if="x.below" class="tag es-t-warning">کمتر از تعرفه</span></div>
        </li>
      </ul>
    </template>
  </div>
</template>
