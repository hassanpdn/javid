// The hotel's public website: its own small page (hotel.html), apart from the demos' app, so a guest downloads only
// this. It borrows the eco-lodge website's layout (eco.css) with the hotel's own colours (hs.css).
// Pages by the address's #: #/ the hotel and the search, #/account the guest's bookings, #/login.
import { createApp } from "vue"
import HotelSite from "./HotelSite.vue"
import "../eco/eco.css"
import "./hs.css"
createApp(HotelSite).mount("#hs")
