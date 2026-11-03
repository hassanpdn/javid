// The eco-lodge's public website: its own small page (lodge.html), apart from the demos' app, so a guest downloads
// only this. Pages by the address's #: #/ the lodge, #/unit/3 a unit, #/account the guest's trips, #/login.
import { createApp } from "vue"
import EcoApp from "./EcoApp.vue"
import "./eco.css"
createApp(EcoApp).mount("#eco")
