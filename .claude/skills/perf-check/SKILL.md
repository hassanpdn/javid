---
name: perf-check
description: Measure how heavy the frontend is and find what makes it slow or laggy (load time on a phone, idle main-thread work, first-visit guide stutter, request waterfall). Use when Hassan says the site is slow, heavy, laggy («سنگین», «کند», «لگ»), before and after a change that adds animation, a page, a dialog or a library, and to check that a speed fix really helped.
---

# Performance check

Measure first, change second, measure again. Numbers come from headless Chromium against the test server, with a
slowed CPU (4x) and, for loading, a slow phone connection. Headless does not show GPU cost (blur, big shadows), so
those are judged from the rules in `reference.md`, not from these numbers.

## Steps

1. Start the test server with the default school set up:
   `bash .claude/skills/perf-check/scripts/serve.sh` (add `HUB=1` in front to also get the assistants page and fabric).
2. Build the frontend so the server serves the current code: `cd frontend && pnpm build`.
3. From `frontend/`, run the modes you need (`node ../.claude/skills/perf-check/scripts/perf.cjs <mode> [role]`):
   - `load`: phone load. Watch `login` (ms to the login page), `kbBeforeLogin`, `panel` (ms from a role to its panel).
   - `idle`: a panel left alone. `styleRecalcs` near 0 is right; about 300 in 5 s means an endless main-thread animation.
   - `which`: names the animation behind the recalcs (60/s = it is not on the graphics card).
   - `tour`: the first-visit guide, desktop and phone. `p95` should stay 16.7 ms and `over50` near 0.
   - `wf`: the request waterfall to the login page. Look for requests that wait on each other but need not.
   - `net iran` (server started with `HUB=1`): every page (assistants page, school login and four panels, fabric,
     real estate, deed) the way a visitor reaches it, on a simulated bad Iranian mobile network: 400 kbit/s, 400 ms
     round trip, 3% packet loss. `net 4g` is the same walk on the slow 4G of `load`, for comparison. Watch `totalMs`
     (median of 3), `worstTotalMs`, `slowest` (the request that took longest) and `retryToasts` (times a page gave up
     and offered «دوباره امتحان کنید»). Chromium's own throttling ignores packet loss, so this mode plays the network
     itself; see `simulate()` in `perf.cjs`.
   Role is the Persian name on the card: مدیر, «پرسنل اداری», مشاور, ولی, آموزگار.
4. To get the "before" numbers, `git stash -u`, rebuild nothing (the old `static/` comes back with the stash), measure,
   then `git stash pop`. The server reads `static/` on every request, so it needs no restart.
5. Fix by the rules in `reference.md`, rebuild, measure again, and report before and after in numbers.
6. Stop the server: `pkill -f "[s]erve.py"; pkill -f "[u]vicorn app:app"` (run it as its own command: a pattern
   that also appears elsewhere in the same command line kills that shell too).

Then the usual done-list from CLAUDE.md: `pnpm build` with `static/` in the commit, the e2e tests when the change
touches every panel, a look at desktop and 360px.

## Bad network (2026-11-02, `net iran` against `net 4g`, median of 3, ms from the first byte to a usable page)

| page | 4g | iran |
|---|---|---|
| assistants page | 2008 | 4855 |
| school login | 2716 | 6528 |
| school مدیر | 6222 | 12942 |
| school پرسنل اداری | 5175 | 10637 |
| school مشاور | 4444 | 9693 |
| school ولی | 4741 | 10806 |
| fabric owner | 5963 | 14681 |
| real estate owner | 6019 | 14270 |
| deed | 3037 | 7806 |

No page gave up («دوباره امتحان کنید» never appeared). Slowest request on iran: a Vazirmatn font, 3.5 to 5.5 s.

## Last results (2026-10-29, after the speed pass)

- Phone, first screen: login page ~2.1 s (was ~2.9 s), 101 KB before it (was 168 to 268 KB).
- First download: ~165 KB of JS (was one 435 KB file); each panel, dialog and drawer comes in its own file.
- Manager's panel standing still: 0.13 s of main-thread work per 5 s (was 3.7 s), 0 layouts (was 60 a second).
- Guide on the manager's panel, desktop: style time 0.9 s (was 1.6 s) over the same steps.
