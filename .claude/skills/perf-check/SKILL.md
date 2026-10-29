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
   Role is the Persian name on the card: مدیر, «پرسنل اداری», مشاور, ولی, آموزگار.
4. To get the "before" numbers, `git stash -u`, rebuild nothing (the old `static/` comes back with the stash), measure,
   then `git stash pop`. The server reads `static/` on every request, so it needs no restart.
5. Fix by the rules in `reference.md`, rebuild, measure again, and report before and after in numbers.
6. Stop the server: `pkill -f "[s]erve.py"; pkill -f "[u]vicorn app:app"` (run it as its own command: a pattern
   that also appears elsewhere in the same command line kills that shell too).

Then the usual done-list from CLAUDE.md: `pnpm build` with `static/` in the commit, the e2e tests when the change
touches every panel, a look at desktop and 360px.

## Last results (2026-10-29, after the speed pass)

- Phone, first screen: login page ~2.1 s (was ~2.9 s), 101 KB before it (was 168 to 268 KB).
- First download: ~165 KB of JS (was one 435 KB file); each panel, dialog and drawer comes in its own file.
- Manager's panel standing still: 0.13 s of main-thread work per 5 s (was 3.7 s), 0 layouts (was 60 a second).
- Guide on the manager's panel, desktop: style time 0.9 s (was 1.6 s) over the same steps.
