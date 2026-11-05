<script setup>
// Every learner, searched by name or mobile: this term's class and the next term's, if any. A row opens the file.
import { ref, watch, onMounted } from "vue"
import { api, fa, retryable } from "../lib/api.js"
import Icon from "../components/Icon.vue"
import Skeleton from "../components/Skeleton.vue"

const emit = defineEmits(["open"])
const q = ref(""), rows = ref(null)
const load = async () => { rows.value = await api("/lang/students?q=" + encodeURIComponent(q.value.trim())) }
onMounted(() => retryable(load))
let timer
watch(q, () => { clearTimeout(timer); timer = setTimeout(() => load().catch(() => {}), 250) })
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="k-toolbar"><input v-model="q" class="k-search" placeholder="جستجو با نام یا شماره‌ی همراه" aria-label="جستجوی زبان‌آموز"></div>
    <Skeleton v-if="!rows" kind="row" :count="8" />
    <p v-else-if="!rows.length" class="muted small">زبان‌آموزی پیدا نشد.</p>
    <ul v-else class="k-list">
      <li v-for="s in rows" :key="s.id">
        <button :class="['card', 'k-row', 'lg-lv', 'lv-' + (s.level || 'S')]" @click="emit('open', s.id)">
          <span :class="['tint', 't-primary']"><Icon name="user" :size="20" /></span>
          <span class="k-row-body"><b>{{ s.name }}</b><span class="k-meta" dir="ltr" style="text-align: right">{{ fa(s.phone) }}</span>
            <span class="k-tags"><span v-if="s.now" class="lg-chip">این ترم: {{ s.now }}</span><span v-if="s.next" class="tag k-t-success">ترم بعد: {{ s.next }}</span>
              <span v-if="!s.now && !s.next" class="tag k-t-secondary">کلاس ندارد</span></span></span>
          <Icon name="chevron" :size="18" class="k-go" />
        </button>
      </li>
    </ul>
  </div>
</template>
