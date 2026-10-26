<script setup>
// The fabric assistant's root: its setup form (first run, or when asked for), its login, or the role's panel.
import { onMounted, watch } from "vue"
import { api, fabricSession, clearFabricSession, lockScroll } from "../lib/api.js"
import { shop, loadShop } from "./lib.js"
import FabricSetup from "./FabricSetup.vue"
import FabricLogin from "./FabricLogin.vue"
import OwnerPanel from "./OwnerPanel.vue"
import SellerPanel from "./SellerPanel.vue"
import AccountantPanel from "./AccountantPanel.vue"

onMounted(async () => {
  try { await loadShop() } catch { shop.loaded = true }
  if (shop.set_up && fabricSession.token && !fabricSession.user) {
    try { fabricSession.user = await api("/fabric/me") } catch { clearFabricSession() }
  }
})
watch(() => fabricSession.user, () => lockScroll(false))
</script>

<template>
  <template v-if="!shop.loaded"></template>
  <FabricSetup v-else-if="!fabricSession.user && (!shop.set_up || shop.setupOpen)" />
  <FabricLogin v-else-if="!fabricSession.user" />
  <OwnerPanel v-else-if="fabricSession.user.role === 'owner'" />
  <SellerPanel v-else-if="fabricSession.user.role === 'seller'" />
  <AccountantPanel v-else />
</template>
