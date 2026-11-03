<script setup>
// The guest's own account: a mobile number and a password they choose. A number the host already entered from a
// phone booking becomes theirs when they register, so they see that booking too. For the demo, the sample guest's
// number and password are written under the form.
import { ref, reactive } from "vue"
import { call, signIn, go, fa } from "./api.js"

const props = defineProps({ next: { type: String, default: "" } })
const tab = ref("login"), f = reactive({ name: "", phone: "", password: "" }), busy = ref(false), error = ref("")
async function submit() {
  busy.value = true; error.value = ""
  try {
    const r = tab.value === "login" ? await call("/login", { phone: f.phone, password: f.password }) : await call("/register", { ...f })
    signIn(r.token, r.guest.name); go(props.next || "/account")
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
</script>

<template>
  <div class="eco-wrap eco-page">
    <form class="eco-narrow eco-panel" @submit.prevent="submit">
      <h1 style="font-size: 22px">{{ tab === 'login' ? 'ورود به حساب' : 'ساخت حساب' }}</h1>
      <div class="eco-tabs" role="tablist"><button type="button" role="tab" :aria-selected="tab === 'login'" :class="{ on: tab === 'login' }" @click="tab = 'login'">ورود</button>
        <button type="button" role="tab" :aria-selected="tab === 'new'" :class="{ on: tab === 'new' }" @click="tab = 'new'">حساب جدید</button></div>
      <label v-if="tab === 'new'" class="eco-field"><span>نام و نام خانوادگی</span><input v-model="f.name" maxlength="60" autocomplete="name" required></label>
      <label class="eco-field"><span>شماره‌ی همراه</span><input v-model="f.phone" dir="ltr" inputmode="tel" autocomplete="tel" maxlength="20" placeholder="09121234567" required></label>
      <label class="eco-field"><span>رمز {{ tab === 'new' ? '(دست‌کم ۶ حرف)' : '' }}</span><input v-model="f.password" type="password" dir="ltr" :autocomplete="tab === 'new' ? 'new-password' : 'current-password'" required></label>
      <p v-if="error" class="eco-msg bad">{{ error }}</p>
      <button class="eco-btn main" :disabled="busy">{{ busy ? 'لطفاً صبر کنید…' : tab === 'login' ? 'ورود' : 'ساخت حساب' }}</button>
      <p class="eco-msg info">برای دیدن پنل یک مهمان نمونه: شماره <span dir="ltr">{{ fa('09120000000') }}</span> و رمز <span dir="ltr">{{ fa('1234') }}</span></p>
    </form>
  </div>
</template>
