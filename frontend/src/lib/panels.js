// Each role's panel is its own file in the build (see App.vue). The login page starts downloading the panel as soon
// as a role is picked, at the same time as the login request, instead of after it.
export const PANELS = {
  manager: () => import("../pages/ManagerPanel.vue"),
  staff: () => import("../pages/StaffPanel.vue"),
  counselor: () => import("../pages/CounselorPanel.vue"),
  parent: () => import("../pages/ParentPanel.vue"),
  chat: () => import("../pages/ChatPage.vue"),   // teachers and students: only questions about the rules for now
}
