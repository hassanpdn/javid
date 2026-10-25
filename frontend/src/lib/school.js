import { reactive } from "vue"
import { api } from "./api.js"

// The school this demo is set up for, loaded before login. Every page reads names from here
// instead of having "Javid" written in, so the same app can be shown for any school.
export const schoolInfo = reactive({ loaded: false, set_up: true, school: {}, saved: [], default: {}, needs_password: false, names: {} })
// true while the setup form is open (on the first run, or from the login page's «مدرسه دیگر»)
export const setupUi = reactive({ open: false })

export async function loadSchool() {
  Object.assign(schoolInfo, await api("/school"), { loaded: true })
  document.title = `دستیار هوشمند ${schoolInfo.school.full_name}`
}
