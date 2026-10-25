import { reactive } from "vue"

// Whether the floating assistant window is open. Any page can open it, e.g. the parent's
// "ask about my child" button, by setting chatUi.open = true.
export const chatUi = reactive({ open: false })
