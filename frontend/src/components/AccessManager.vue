<script setup>
// «دسترسی‌ها» on the assistants page, for the permanent account only (access.py): everyone given access, which
// assistants they see and until when. New access, changes and removal happen here (AccessForm for the details).
import { ref, onMounted } from "vue"
import { accessCall, jalaliText } from "../lib/access.js"
import Icon from "./Icon.vue"
import AccessForm from "./AccessForm.vue"

const props = defineProps({ assistants: Array })
const list = ref([]), loading = ref(true), editing = ref(null), adding = ref(false), removing = ref(null)

const load = async () => {
  try { list.value = await accessCall("/access/people") } catch {}
  loading.value = false
}
onMounted(load)

const app = (key) => props.assistants.find((a) => a.key === key) || { title: key, icon: "sparkles", hue: "violet" }
const lastLogin = (sec) => sec ? "آخرین ورود: " + new Date(sec * 1000).toLocaleDateString("fa-IR", { day: "numeric", month: "long" }) : "هنوز وارد نشده"
const remove = async (p) => {
  try { await accessCall(`/access/people/${p.id}/delete`, {}) } catch {}
  removing.value = null
  await load()
}
</script>

<template>
  <section class="am">
    <header class="am-head">
      <div class="am-title">
        <span class="am-badge"><Icon name="users" :size="22" /></span>
        <div><h2>دسترسی‌ها</h2><p>چه کسی، با چه رمزی، کدام دستیار را ببیند.</p></div>
      </div>
      <button class="am-add" @click="adding = true"><Icon name="plus" :size="18" />دسترسی تازه</button>
    </header>

    <div v-if="loading" class="am-grid">
      <div v-for="n in 2" :key="n" class="am-person am-skel"><i></i><span><b></b><em></em></span></div>
    </div>
    <div v-else-if="!list.length" class="am-empty">
      <span class="am-empty-icon"><Icon name="userCheck" :size="28" /></span>
      <b>هنوز به کسی دسترسی نداده‌اید</b>
      <p>با «دسترسی تازه» برای هر نفر نام کاربری و رمز بسازید و دستیارهایی را که می‌بیند انتخاب کنید.</p>
    </div>
    <ul v-else class="am-grid">
      <li v-for="p in list" :key="p.id" :class="['am-person', { gone: p.expired }]">
        <span class="am-avatar" :style="{ '--h': (p.id * 67) % 360 }">{{ p.name.trim().charAt(0) }}</span>
        <div class="am-body">
          <div class="am-row">
            <b class="am-name">{{ p.name }}</b>
            <span :class="['am-state', p.expired ? 'off' : 'on']">{{ p.expired ? "تمام شده" : "فعال" }}</span>
          </div>
          <span class="am-user" dir="ltr">{{ p.username }}</span>
          <div class="am-apps">
            <span v-for="k in p.apps" :key="k" :class="['am-app', 'hue-' + app(k).hue]"><Icon :name="app(k).icon" :size="14" />{{ app(k).title }}</span>
          </div>
          <div class="am-meta">
            <span><Icon name="calendar" :size="14" />{{ p.expires_on ? "تا " + jalaliText(p.expires_on) : "بدون تاریخ پایان" }}</span>
            <span><Icon name="clock" :size="14" />{{ lastLogin(p.last_login) }}</span>
          </div>
          <div v-if="removing === p.id" class="am-confirm">
            <span>دسترسی {{ p.name }} پاک شود؟</span>
            <button class="am-btn danger" @click="remove(p)">پاک شود</button>
            <button class="am-btn" @click="removing = null">نه</button>
          </div>
          <div v-else class="am-actions">
            <button class="am-btn" @click="editing = p"><Icon name="pencil" :size="15" />تغییر</button>
            <button class="am-btn" @click="removing = p.id"><Icon name="x" :size="15" />پاک کردن</button>
          </div>
        </div>
      </li>
    </ul>

    <!-- to body: this section's frosted glass would otherwise hold the dialog inside it -->
    <Teleport to="body">
      <AccessForm v-if="adding || editing" :assistants="assistants" :person="editing" @saved="load" @close="adding = false; editing = null" />
    </Teleport>
  </section>
</template>

<style scoped>
.am { width: min(100%, 1120px); margin-top: 18px; padding: 24px; border-radius: 28px; animation: am-up .9s cubic-bezier(.2,.9,.25,1) .5s backwards;
  background: linear-gradient(165deg, rgba(255,255,255,.09), rgba(255,255,255,.025)); border: 1px solid rgba(255,255,255,.12);
  backdrop-filter: blur(22px) saturate(140%); -webkit-backdrop-filter: blur(22px) saturate(140%); box-shadow: 0 30px 80px -30px rgba(0,0,0,.7); }
.am-head { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; margin-bottom: 18px; }
.am-title { display: flex; align-items: center; gap: 14px; }
.am-badge { display: grid; place-items: center; width: 48px; height: 48px; border-radius: 16px; color: #fff;
  background: linear-gradient(135deg, #ff6fa8, #7367f0); box-shadow: 0 10px 26px -8px rgba(255,111,168,.7); }
.am-title h2 { margin: 0; font-size: 20px; color: #fff; }
.am-title p { margin: 2px 0 0; font-size: 13.5px; color: #b7b3d9; }
.am-add { display: inline-flex; align-items: center; gap: 8px; height: 46px; padding: 0 18px; border: 0; border-radius: 14px; cursor: pointer;
  font: inherit; font-size: 14.5px; font-weight: 700; color: #fff; background: linear-gradient(110deg, #6a5cf5, #8f6bff 45%, #1fb8d6); background-size: 180% 100%;
  box-shadow: 0 14px 30px -12px rgba(115,103,240,.9); transition: background-position .5s; }
.am-add:hover { background-position: 100% 0; }
.am-add:focus-visible { outline: 3px solid #8fefff; outline-offset: 3px; }

.am-grid { margin: 0; padding: 0; list-style: none; display: grid; gap: 14px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr)); }
.am-person { display: flex; gap: 14px; padding: 16px; border-radius: 20px; background: rgba(10,9,32,.45); border: 1px solid rgba(255,255,255,.1);
  transition: border-color .2s, transform .2s; }
.am-person:hover { border-color: rgba(255,255,255,.22); }
.am-person.gone { opacity: .6; }
.am-avatar { flex: none; display: grid; place-items: center; width: 48px; height: 48px; border-radius: 50%; font-size: 20px; font-weight: 700; color: #fff;
  background: linear-gradient(140deg, hsl(var(--h) 70% 62%), hsl(calc(var(--h) + 50) 70% 45%)); box-shadow: 0 8px 20px -8px hsl(var(--h) 70% 50%); }
.am-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.am-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.am-name { min-width: 0; color: #fff; font-size: 15.5px; line-height: 1.6; overflow-wrap: anywhere; }
.am-state { flex: none; padding: 2px 10px; border-radius: 999px; font-size: 12px; }
.am-state.on { color: #7ef0b0; background: rgba(62,224,143,.14); }
.am-state.off { color: #ffa3b0; background: rgba(255,111,140,.14); }
.am-user { align-self: flex-start; font-size: 13px; color: #c9c5ee; letter-spacing: .03em; }
.am-apps { display: flex; flex-wrap: wrap; gap: 6px; }
.am-app { --c1: #7367f0; display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px; border-radius: 999px; font-size: 12px; color: #fff;
  background: color-mix(in srgb, var(--c1) 30%, transparent); border: 1px solid color-mix(in srgb, var(--c1) 60%, transparent); }
.am-app.hue-teal { --c1: #12a594; }
.am-meta { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 12.5px; color: #b7b3d9; }
.am-meta span { display: inline-flex; align-items: center; gap: 5px; }
.am-actions, .am-confirm { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 4px; }
.am-confirm span { font-size: 13px; color: #ffd0d8; }
.am-btn { display: inline-flex; align-items: center; gap: 5px; height: 34px; padding: 0 12px; border-radius: 10px; cursor: pointer;
  font: inherit; font-size: 13px; color: #dcd8ff; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12); }
.am-btn:hover, .am-btn:focus-visible { color: #fff; background: rgba(255,255,255,.14); outline: none; }
.am-btn.danger { color: #fff; background: #c93a55; border-color: #c93a55; }

.am-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 28px 16px; text-align: center; border-radius: 20px;
  border: 1px dashed rgba(255,255,255,.18); }
.am-empty-icon { display: grid; place-items: center; width: 60px; height: 60px; border-radius: 50%; color: #c9c3ff; background: rgba(143,133,255,.16); }
.am-empty b { color: #fff; font-size: 15px; }
.am-empty p { margin: 0; max-width: 420px; font-size: 13.5px; line-height: 2; color: #b7b3d9; }

.am-skel i { flex: none; width: 48px; height: 48px; border-radius: 50%; background: rgba(255,255,255,.08); }
.am-skel span { flex: 1; display: flex; flex-direction: column; gap: 10px; }
.am-skel b, .am-skel em { display: block; height: 14px; border-radius: 7px; background: rgba(255,255,255,.08); }
.am-skel b { width: 50%; } .am-skel em { width: 80%; }

@media (max-width: 480px) {
  .am { padding: 18px 14px; border-radius: 24px; }
  .am-add { width: 100%; justify-content: center; }
}
@keyframes am-up { from { opacity: 0; transform: translateY(30px); } }
@media (prefers-reduced-motion: reduce) { .am { animation: none; } }
</style>
