<script setup>
// The hotel's website: a bar with the hotel's name and the guest's account, the page the address asks for, and the
// footer. A banner on every page says it is a demo: nothing is really booked and no money should be paid.
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from "vue"
import { call, guest, fa } from "./api.js"
import HsHome from "./HsHome.vue"
const HsAccount = defineAsyncComponent(() => import("./HsAccount.vue"))
const HsAuth = defineAsyncComponent(() => import("./HsAuth.vue"))

const site = ref(null), error = ref(""), route = ref(location.hash.slice(1) || "/")
const onHash = () => { route.value = location.hash.slice(1) || "/" }
onMounted(async () => {
  addEventListener("hashchange", onHash)
  try { site.value = await call("/site"); document.title = site.value.name } catch (e) { error.value = e.message }
})
onUnmounted(() => removeEventListener("hashchange", onHash))
const page = computed(() => route.value.startsWith("/account") ? "account" : route.value.startsWith("/login") ? "login" : "home")
const back = computed(() => decodeURIComponent(route.value.split("?next=")[1] || ""))
</script>

<template>
  <div class="eco-demo" role="note">این سایت نمایشی است: رزروها واقعی نیستند و پولی واریز نکنید.</div>
  <header class="eco-nav">
    <div class="eco-wrap">
      <a class="eco-brand" href="#/"><i>{{ (site?.name || 'ه').replace('هتل ', '')[0] }}</i><span>{{ site?.name || 'هتل' }}</span></a>
      <nav>
        <a v-if="guest.token" class="eco-btn soft" href="#/account">رزروهای من</a>
        <a v-else class="eco-btn soft" href="#/login">ورود</a>
      </nav>
    </div>
  </header>
  <main>
    <p v-if="error" class="eco-wrap eco-msg bad" style="margin-top: 24px">{{ error }}</p>
    <template v-else-if="site">
      <HsAccount v-if="page === 'account'" :site="site" />
      <HsAuth v-else-if="page === 'login'" :next="back" />
      <HsHome v-else :site="site" />
    </template>
  </main>
  <footer v-if="site" class="eco-foot">
    <div class="eco-wrap">
      <b>{{ site.name }}</b> · {{ site.place }}<br>
      ورود از ساعت {{ fa(site.check_in) }} · خروج تا ساعت {{ fa(site.check_out) }}<br>
      <small>نسخه‌ی نمایشی ساخته‌شده با دستیار هتل</small>
    </div>
  </footer>
</template>
