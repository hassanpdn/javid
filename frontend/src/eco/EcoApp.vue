<script setup>
// The eco-lodge's website: a bar with the lodge's name and the guest's account, the page the address asks for, and
// the footer. A banner on every page says it is a demo: nothing is really booked and no money should be paid.
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from "vue"
import { call, guest, fa, go } from "./api.js"
import EcoHome from "./EcoHome.vue"
const EcoUnit = defineAsyncComponent(() => import("./EcoUnit.vue"))
const EcoAccount = defineAsyncComponent(() => import("./EcoAccount.vue"))
const EcoAuth = defineAsyncComponent(() => import("./EcoAuth.vue"))

const site = ref(null), error = ref(""), route = ref(location.hash.slice(1) || "/")
const onHash = () => { route.value = location.hash.slice(1) || "/" }
onMounted(async () => {
  addEventListener("hashchange", onHash)
  try { site.value = await call("/site"); document.title = site.value.name } catch (e) { error.value = e.message }
})
onUnmounted(() => removeEventListener("hashchange", onHash))
const page = computed(() => route.value.startsWith("/unit/") ? "unit" : route.value.startsWith("/account") ? "account" : route.value.startsWith("/login") ? "login" : "home")
const unitId = computed(() => Number(route.value.split("/")[2]) || 0)
const back = computed(() => decodeURIComponent(route.value.split("?next=")[1] || ""))
</script>

<template>
  <div class="eco-demo" role="note">این سایت نمایشی است: رزروها واقعی نیستند و پولی واریز نکنید.</div>
  <header class="eco-nav">
    <div class="eco-wrap">
      <a class="eco-brand" href="#/"><i>{{ (site?.name || 'ا').replace('اقامتگاه بوم‌گردی ', '')[0] }}</i><span>{{ site?.name || 'اقامتگاه بوم‌گردی' }}</span></a>
      <nav>
        <a v-if="guest.token" class="eco-btn soft" href="#/account">سفرهای من</a>
        <a v-else class="eco-btn soft" href="#/login">ورود</a>
      </nav>
    </div>
  </header>
  <main>
    <p v-if="error" class="eco-wrap eco-msg bad" style="margin-top: 24px">{{ error }}</p>
    <template v-else-if="site">
      <EcoUnit v-if="page === 'unit'" :key="unitId" :id="unitId" :site="site" />
      <EcoAccount v-else-if="page === 'account'" :site="site" />
      <EcoAuth v-else-if="page === 'login'" :next="back" />
      <EcoHome v-else :site="site" />
    </template>
  </main>
  <footer v-if="site" class="eco-foot">
    <div class="eco-wrap">
      <b>{{ site.name }}</b> · {{ site.place }}<br>
      میزبان: {{ site.host }} · تلفن: <span dir="ltr">{{ fa(site.words.phone) }}</span><br>
      <small>نسخه‌ی نمایشی ساخته‌شده با دستیار اقامتگاه بوم‌گردی</small>
    </div>
  </footer>
</template>
