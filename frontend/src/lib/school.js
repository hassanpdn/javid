import { reactive } from "vue"
import { api } from "./api.js"

// The school this demo is set up for, loaded before login. Every page reads names from here
// instead of having "Javid" written in, so the same app can be shown for any school.
export const schoolInfo = reactive({ loaded: false, set_up: true, school: {}, names: {}, features: { parents: true, students: true } })
// true while the setup form is open (on the first run, or from the login page's «مدرسه دیگر»)
export const setupUi = reactive({ open: false })

// Switch the parent / student roles on or off. The server applies it at once (no data rebuild).
export async function setFeatures(changes) {
  const { features } = await api("/features", { ...schoolInfo.features, ...changes })
  schoolInfo.features = features
}

export async function loadSchool() {
  Object.assign(schoolInfo, { school: {}, names: {} }, await api("/school"), { loaded: true })
  document.title = schoolInfo.school.full_name ? `دستیار هوشمند ${schoolInfo.school.full_name}` : "دستیار هوشمند مدرسه"
}
