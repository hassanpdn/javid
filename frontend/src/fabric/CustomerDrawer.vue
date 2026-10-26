<script setup>
// A customer's card in a side drawer, for the owner's and the accountant's lists.
import Icon from "../components/Icon.vue"
import CustomerCard from "./CustomerCard.vue"
defineProps({ id: Number })
defineEmits(["close"])
</script>

<template>
  <div class="overlay" @click.self="$emit('close')">
    <aside class="drawer" v-drawer aria-label="کارت مشتری">
      <div class="drawer-head">
        <b class="text-ink">کارت مشتری</b>
        <button class="icon-btn" @click="$emit('close')" aria-label="بستن"><Icon name="x" /></button>
      </div>
      <div class="drawer-body" tabindex="0"><CustomerCard :id="id" /></div>
    </aside>
  </div>
</template>
