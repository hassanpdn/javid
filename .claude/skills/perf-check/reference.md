# What keeps this frontend light

Learned on this codebase; each line says what to do and why.

## Animation

- Endless motion (`repeat: -1`, pulsing, floating, spinning) is a CSS `@keyframes` animation, never GSAP. An endless
  GSAP tween writes a style from JavaScript on every frame, forever: on the manager's panel that was 60 style recalcs
  and 60 layouts a second with nobody touching the page, and the first-visit guide stuttered on top of it.
- Animate only `translate`, `scale`, `rotate` (the separate properties) and `opacity`. They run on the graphics card
  and add to GSAP's `transform` instead of fighting it. `right`, `top`, `width`, `background-position` and
  `box-shadow` re-lay or repaint the page on every frame (`fg-run` moved with `right` until it was changed).
- Parts inside an `<svg>`, and an `<svg>` element itself, are not moved by the graphics card even with CSS. A moving
  part gets its own small svg wrapped in an HTML element, and the wrapper is animated (see `AiOrb.vue`). The login
  page's drawing still animates parts inside one svg: it costs about 60 recalcs a second while that page is open.
- One-off entrances (`v-reveal`, `v-pop`, `v-drawer`, page intros) stay in GSAP: they end.
- `main.css` pauses the endless loops while a guide is open (`.driver-active ... { animation-play-state: paused }`) and
  turns off the bars' blur under the guide's overlay. A new endless loop on a panel goes into that list.
- Wrap new endless animations in `@media (prefers-reduced-motion: no-preference)`.
- The first thing a page shows (its LCP element: the door's card, a hero title) never fades in from `opacity: 0`.
  Text that starts invisible counts as not shown until the fade ends: the door's 0.9 s fade put PageSpeed's LCP at
  2.6 s. Slide or scale it in instead (door: 2.5 s -> 1.8 s on the phone profile).

## Class names

- Tailwind builds a utility for any class name that matches one, even in a scoped style: a part called `ring` got
  Tailwind's 1px ring as a frame. Prefix a component's own parts (`o-ring`, `dp-...`).

## Loading

- Every page in `App.vue` and every role's panel (`lib/panels.js`) is `defineAsyncComponent`: its code downloads only
  when it is shown. The fabric assistant's screens likewise (`fabric/FabricApp.vue`).
- Anything shown only after a click (dialogs, drawers, a second page inside a panel, the chat window's `ChatBox`) is
  `defineAsyncComponent` too, behind its `v-if`. A new one follows the same pattern.
- Start downloads that will be needed in parallel with the request that decides them: the login page asks for the
  panel's code at the same time as `/login`; `App.vue` asks `/gate/status` and `/access/status` together, `/school`
  and `/me` together, and fetches the setup and login pages while `/school` is on its way.
- driver.js and its CSS are imported inside `runTour` (`lib/tour.js`), only when a guide is about to run.
- GSAP is not in the first download (it was 26 KB of the door's 37 KB first file, PageSpeed's "unused JavaScript").
  `lib/motion.js` loads it a second after the page's load event; its directives show the element without animating
  until it is there. Components that animate import `gsap` themselves, in the pages' own files. Never import GSAP
  from anything `main.js` loads.
- The door (`GatePage.vue`) is all English and uses the system font, so it downloads no font; Vazirmatn (two 50 KB
  files) loads with the first Persian page.
- No `<link rel="preload">` for the fonts: on a slow phone connection they took bandwidth from the JavaScript the first
  screen needs. They load with `font-display: swap`.
- `app.py` serves `static/assets/*` (hashed names) with a one-year immutable cache and everything else with
  `no-cache`, so a returning visitor downloads nothing that did not change.

## Selectors

- No `html:has(...)` or `body:has(...)` rules for state; set a class from JavaScript (`html.touring` in `lib/tour.js`).
