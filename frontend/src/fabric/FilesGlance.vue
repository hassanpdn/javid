<script setup>
// The three Excel files in one picture: stock, sales and accounts, the links between them, and whether they agree.
// The dots running along a link are the checks; a link turns red where the files stop agreeing.
// pulse: names of files that just changed (from the event log); they light up for a moment.
import { computed } from "vue"
import { fa } from "../lib/api.js"
import Icon from "../components/Icon.vue"

const props = defineProps({ glance: Object, pulse: { type: Array, default: () => [] }, compact: { type: Boolean, default: false } })
defineEmits(["details"])
const file = (key) => props.glance.files.find((f) => f.key === key)
const ICON = { stock: "inbox", sales: "chart", accounts: "file" }
const count = computed(() => props.glance.issues.length)
const short = (iso) => iso ? fa(iso.slice(11, 16)) : ""
</script>

<template>
  <section :class="['card', 'fg', { bad: count }]">
    <div class="fg-head">
      <span :class="['tint', 'lg', count ? 't-danger' : 't-success']"><Icon :name="count ? 'alert' : 'shield'" :size="24" /></span>
      <div class="grow">
        <b>{{ count ? `${fa(count)} مغایرت بین فایل‌ها پیدا شد` : 'سه فایل با هم جور است' }}</b>
        <small class="muted">هر فاکتور، هر توپ پارچه و هر ریال بین انبار، فروش و حسابداری تطبیق داده می‌شود.</small>
      </div>
      <button v-if="!compact" class="btn sm" @click="$emit('details')">{{ count ? 'دیدن مغایرت‌ها' : 'جزئیات' }}</button>
    </div>

    <div class="fg-map">
      <template v-for="(key, i) in ['stock', 'sales', 'accounts']" :key="key">
        <div v-if="i" :class="['fg-link', glance.links[i === 1 ? 'sales_stock' : 'sales_money'] ? 'ok' : 'off']" aria-hidden="true">
          <i></i><i></i><i></i>
        </div>
        <div :class="['fg-node', { pulse: pulse.includes(file(key).name) }]">
          <span class="fg-icon"><Icon :name="ICON[key]" :size="22" /><em>XLSX</em></span>
          <b>{{ file(key).name }}</b>
          <small>{{ fa(file(key).count) }} {{ file(key).unit }}</small>
          <small v-if="file(key).last" class="fg-last">{{ short(file(key).last.at) }} · {{ file(key).last.who }}</small>
        </div>
      </template>
    </div>

    <ul class="fg-checks">
      <li v-for="ch in glance.checks" :key="ch.key" :class="ch.ok ? 'ok' : 'off'">
        <Icon :name="ch.ok ? 'check' : 'alert'" :size="15" /><span><b>{{ ch.title }}</b> {{ fa(ch.text) }}</span>
      </li>
    </ul>
  </section>
</template>
