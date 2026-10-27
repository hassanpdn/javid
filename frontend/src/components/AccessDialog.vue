<script setup>
// The login box that opens on a card of the assistants page when this browser may not open it yet (access.js).
// The permanent account opens every card; a guest's one-time password only the cards it was made for.
import { ref, onMounted } from "vue"
import { access, enterAccess, canOpen } from "../lib/access.js"
import Icon from "./Icon.vue"
import "./hub-dialog.css"

const props = defineProps({ app: String, title: String })
const emit = defineEmits(["close", "opened"])
const username = ref(""), password = ref(""), show = ref(false)
const error = ref(""), sending = ref(false)
const userEl = ref(null)
onMounted(() => { if (window.matchMedia("(min-width: 768px)").matches) userEl.value?.focus() })

const submit = async () => {
  if (sending.value) return
  if (!username.value.trim() || !password.value) { error.value = "نام کاربری و رمز عبور را بنویسید."; return }
  sending.value = true; error.value = ""
  const msg = await enterAccess(username.value, password.value)
  sending.value = false
  if (msg) { error.value = msg; password.value = ""; return }
  if (!canOpen(props.app)) { error.value = "این رمز برای دستیار دیگری است."; return }
  emit("opened", props.app)
}
</script>

<template>
  <div class="hd-overlay" @click.self="emit('close')">
    <form class="hd" v-pop @submit.prevent="submit" novalidate>
      <div class="hd-head">
        <div>
          <h3>ورود به {{ title }}</h3>
          <p>{{ access.guest ? "رمزی که با آن وارد شده‌اید این دستیار را باز نمی‌کند." : "نام کاربری و رمزی را که گرفته‌اید بنویسید." }}</p>
        </div>
        <button type="button" class="hd-x" aria-label="بستن" @click="emit('close')"><Icon name="x" :size="18" /></button>
      </div>
      <label class="hd-field">
        <span class="hd-label">نام کاربری</span>
        <span class="hd-input">
          <Icon name="user" :size="19" />
          <input ref="userEl" v-model="username" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" dir="ltr" />
        </span>
      </label>
      <label class="hd-field">
        <span class="hd-label">رمز عبور</span>
        <span class="hd-input">
          <Icon name="lock" :size="19" />
          <input v-model="password" name="password" :type="show ? 'text' : 'password'" autocomplete="current-password" dir="ltr" />
          <button type="button" class="hd-eye" :aria-label="show ? 'پنهان کردن رمز' : 'نشان دادن رمز'" :aria-pressed="show" @click="show = !show">
            <Icon :name="show ? 'eyeOff' : 'eye'" :size="19" />
          </button>
        </span>
      </label>
      <p class="hd-error" role="alert">{{ error }}</p>
      <button class="hd-btn" :disabled="sending">
        <span v-if="sending" class="hd-spin" aria-hidden="true"></span>
        {{ sending ? "در حال ورود" : "ورود" }}
      </button>
    </form>
  </div>
</template>
