<script setup>
// Chat with the assistant. endpoint/examples/intro let other panels reuse it
// (e.g. the parent asks about their own child at /parent/ask).
import { ref, computed, nextTick } from "vue"
import { api, fa, session } from "../lib/api.js"
import Icon from "./Icon.vue"
import AiOrb from "./AiOrb.vue"

const EXAMPLES = {
  manager: ["ساعت کار کارکنان اداری چقدر است؟", "آیا مدرسه‌ی غیرانتفاعی مالیات می‌پردازد؟", "کلاس‌ها چه ساعتی شروع می‌شوند؟"],
  staff: ["سال مالی مدرسه از چه زمانی شروع می‌شود؟", "آیا مدرسه باید حساب بانکی جداگانه داشته باشد؟", "غیبت بیماری را تا چه زمانی باید اطلاع داد؟"],
  default: ["کلاس‌ها چه ساعتی شروع می‌شوند؟", "اگر فرزندم بیمار شود، غیبتش چگونه موجه می‌شود؟", "آیا استفاده از تلفن همراه در مدرسه مجاز است؟"],
}
const props = defineProps({
  endpoint: { default: "/chat" }, examples: { default: null }, intro: { default: null },
  loadingText: { default: "در حال جستجو در اسناد" },
})
const messages = ref([]), input = ref(""), loading = ref(false), box = ref(null)
const shownExamples = computed(() => props.examples || EXAMPLES[session.user?.role] || EXAMPLES.default)
const scrollDown = async () => { await nextTick(); box.value?.scrollTo({ top: box.value.scrollHeight, behavior: "smooth" }) }
const send = async (text) => {
  const question = text.trim()
  if (!question || loading.value) return
  messages.value.push({ from: "user", text: question }); input.value = ""; loading.value = true; scrollDown()
  try {
    const data = await api(props.endpoint, { question })
    messages.value.push({ from: "bot", text: data.answer, sources: data.sources, checked: data.checked })
  } catch (e) {
    if (e.message !== "401") messages.value.push({ from: "bot error", text: "ارتباط با سرور برقرار نشد. چند لحظه بعد دوباره امتحان کنید." })
  } finally { loading.value = false; scrollDown() }
}
</script>

<template>
  <div class="chatbox">
    <div class="chat" ref="box" role="log" aria-live="polite">
      <div v-if="messages.length === 0" class="empty">
        <AiOrb :size="80" />
        <p>{{ intro || 'سؤال خود را درباره‌ی آیین‌نامه‌ها و دستورالعمل‌ها بپرسید یا یکی از این نمونه‌ها را امتحان کنید:' }}</p>
        <div class="examples">
          <button v-for="ex in shownExamples" :key="ex" class="example" @click="send(ex)"><Icon name="sparkles" :size="16" />{{ ex }}</button>
        </div>
      </div>
      <div v-for="(m, i) in messages" :key="i" v-reveal :class="['msg-row', m.from]">
        <span v-if="m.from !== 'user'" class="bot-avatar sm"><Icon name="sparkles" :size="15" /></span>
        <div class="msg">
          <div class="bubble">{{ fa(m.text) }}</div>
          <div v-if="m.sources && m.sources.length" class="sources">
            <span>منبع:</span>
            <span v-for="s in m.sources" :key="s.doc + s.article" class="chip">{{ s.doc }}{{ s.article ? '، ' + fa(s.article) : '' }}</span>
            <span v-if="m.checked" class="muted small">· عددها مستقیم از سامانه مدرسه</span>
          </div>
        </div>
      </div>
      <div v-if="loading" class="msg-row bot">
        <span class="bot-avatar sm"><Icon name="sparkles" :size="15" /></span>
        <div class="msg"><div class="bubble loading typing"><span class="typing-dots"><i></i><i></i><i></i></span><small>{{ loadingText }}</small></div></div>
      </div>
    </div>
    <form class="composer" @submit.prevent="send(input)">
      <input v-model="input" :disabled="loading" placeholder="سؤال خود را اینجا بنویسید..." aria-label="متن سؤال">
      <button class="btn primary" type="submit" :disabled="loading || !input.trim()"><Icon name="send" :size="18" /><span>ارسال</span></button>
    </form>
  </div>
</template>
