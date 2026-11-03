# Architecture of the whole application

This is the map. Each assistant has its own document next to its code:

| Assistant | Code | Its document |
|---|---|---|
| School (the first one) | files at the root (`app.py`, `staff.py`, `manager.py`, ...) | [ARCHITECTURE-school.md](ARCHITECTURE-school.md) |
| Fabric wholesaler | `fabric/` | [fabric/ARCHITECTURE.md](fabric/ARCHITECTURE.md) |
| Deed data extraction | `deed/` | [deed/ARCHITECTURE.md](deed/ARCHITECTURE.md) |
| Real estate agency | `estate/` | [estate/ARCHITECTURE.md](estate/ARCHITECTURE.md) |
| Law office | `law/` | [law/ARCHITECTURE.md](law/ARCHITECTURE.md) |
| Dental clinic | `dental/` | [dental/ARCHITECTURE.md](dental/ARCHITECTURE.md) |
| Hotel | `hotel/` | [hotel/ARCHITECTURE.md](hotel/ARCHITECTURE.md) |
| Eco-lodge, with its public website | `lodge/`, `frontend/src/eco/` | [lodge/ARCHITECTURE.md](lodge/ARCHITECTURE.md) |

`CLAUDE.md` is the working rulebook (how code is written here). `PRODUCTION.md` is what it takes to give an
assistant to a real customer. This file explains what the application is made of and why.

## In one minute

One web application holds several AI assistants for different businesses. Each assistant is a small, separate
product: its own data, its own logins, its own screens. They share one server, one website and a few common pieces
(the model client, the checks on model output, Jalali dates, the site's door).

The idea behind every assistant is the same: **code does the work that must be right, the model does the work that
must read or sound human.** Numbers, dates, prices, deadlines and rules are computed by plain functions. The model
reads messy text people paste (a WhatsApp message, a court notice, a letter) and writes sentences (a morning summary,
a message to a client). Every sentence it writes is checked against the computed facts before anyone sees it, and if
the check fails, or the model is off or slow, a sentence built by code is shown instead. A person always decides
anything that leaves the office.

## The shape

```
 Browser (Vue single-page app, built into static/)
   │  one fetch helper (frontend/src/lib/api.js): token per assistant, time limits, one retry for reads
   ▼
 FastAPI app (app.py)
   │  middleware: the site's door (gate.py) → the assistant's login (access.py) → which assistant's AI switch
   ├── /school routes (app.py, manager.py, staff.py, counselor.py, parent.py, ...)   → school.db + vector store db/
   ├── /fabric/...  (fabric/api.py, fabric/shop.py)                                  → fabric.db + three Excel files
   ├── /deed/...    (deed/api.py)                                                    → deed.db + scanned files
   ├── /estate/...  (estate/api.py, estate/site.py)                                  → estate.db
   ├── /law/...     (law/api.py)                                                     → law.db
   ├── /dental/...  (dental/api.py)                                                  → dental.db
   ├── /hotel/...   (hotel/api.py, hotel/site.py)                                    → hotel.db
   ├── /lodge/...   (lodge/api.py; lodge/public.py is public, with guests' accounts)   → lodge.db + photos
   ├── /access/..., /gate/..., /speed                                                → access.db
   └── static files (the built website), mounted last
 Shared: llm.py (the model), checks.py (checks on model text), jalali.py (dates), offline.py (school texts without AI)
```

Inside every assistant the layers are the same, and they only call downward:

```
 api.py      thin routes: check the input and the role, call facts, return JSON
   ▼
 facts.py    plain functions: every number, date, price, rule, alert and check (no web, no model)
   ▼
 store.py    the SQLite database: schema, connection, users and sessions, the event log
 demo.py     builds believable demo data around today, with planted situations
 read.py     reads pasted text: rules first, the model optionally, every value checked against the text
 info.py     the business being shown (name, people), from a small JSON file
```

This is the common "layered" design (routes, domain logic, storage) with a "functional core": the important logic
is in plain functions that take a database connection and return data, so it can be tested without a browser or a
model.

## Why it is built this way

**One application, many packages (a modular monolith), not one service per assistant.** One process is one thing to
run, deploy, watch and back up. Each assistant is still separate: its own package, database and logins, and none of
them imports another's data. Taking one assistant to a customer means copying its package plus the shared files.
Splitting into services would add networking, more deploys and more failure points, for a demo with a handful of
users. If one assistant ever needs to scale alone, its package already has a clean edge to cut along.

**SQLite, one file per assistant.** No database server to install, which matters because a real customer gets the
assistant on one office computer without internet (see `PRODUCTION.md`). One file per assistant means resetting one
demo never touches another, and a customer's data is one file to back up. The known limit: SQLite has one writer at a
time. That is fine for an office of a few people; the code sends notifications only after a write commits so writers
never wait on each other.

**Plain SQL, no ORM.** The queries are short and visible where they are used. A reader sees exactly what is asked of
the database. An ORM would add a layer to learn for little gain at this size.

**FastAPI + Pydantic.** Every request body is a typed model, so wrong input is refused with a clear error before any
code runs. Roles are checked by a dependency on each route (`require("owner")`), never by reading the request body.

**Vue single-page app, built and committed into `static/`.** The server needs no Node.js; the same Python process
serves the site and the API from one address (no CORS). Pages, dialogs and drawers are split into separate files
loaded on demand, so a visitor downloads only what they open. Every page talks to the server through `lib/api.js`
only, and pages never compute a business number: the server sends it ready to show.

**The model only reads and writes text (guardrails).** Language models are good at reading messy text and writing
natural sentences, and bad at arithmetic, dates and rules. So:
- Computing: always code (`facts.py`).
- Reading pasted text (`read.py`): rules read it first; the model may fill gaps; every value it proposes must be
  found in the text itself, otherwise it is dropped. Each value is shown with the words it came from.
- Writing (`_written()` in each `api.py`): the model gets only computed facts; `checks.only_known_numbers()` refuses
  any text with a number that is not in those facts; then a code-built text is shown instead. Parent-facing text in
  the school also goes through `checks.unsafe_for_parent()` (no diagnosis, no comparison, no private notes).
- Off or slow: `llm.ask_llm()` raises `ModelOff` when the assistant's AI switch is off and `ModelDown` after
  `LLM_TIMEOUT` seconds (15) or any provider error. Every caller catches both and uses the same code-built text, so
  the screens look the same with or without AI.

**Human in the loop.** Messages to clients, parents, guests and patients are drafts a person copies and sends.
Bookings, payments, cancellations and decisions are buttons a person presses. The assistant suggests and explains.

**Every number explains itself.** Most numbers on a dashboard have «از کجا؟» next to them: the sum behind it, line
by line. Checks (the «بررسی‌ها» pages) say what does not add up and show the records, never who is to blame.

**Planted situations in demo data.** Each `demo.py` builds a believable business around today's date with a fixed
random seed, and plants a few problems (a missed deadline, a room sold twice, a cheque that bounced). The panels must
find each one by themselves from the data. Tests check that each is found exactly once, which also proves the rules
do not raise false alarms on the ordinary data around them.

**Configuration by environment variables.** Paths, model address, timeouts and the live site's switches come from
`.env` (never committed). The same code runs locally, in tests and on the server.

## Security, in layers

1. The site's door (`gate.py`, live site only): one username and password before anything; a signed cookie for 30
   days. Every API call without it gets 401.
2. Access to each assistant (`access.py`, live site only): the permanent account opens everything and gives other
   people accounts for chosen assistants, with an optional expiry. Every login try is logged.
3. Each assistant's own login and roles: a token per assistant (a school token never works on `/fabric/...`), and
   each route states which roles may call it.
4. Data rules inside an assistant: a parent sees only their own child (the id comes from the login, never the
   question); the counselor's notes never reach a parent or a parent-facing prompt; vector search always filters by
   role.

## Dates

Iran uses the Jalali calendar. The database stores ISO dates (`2026-11-03`), because they sort and compare correctly.
Everything shown or typed is Jalali (`1405/08/12`, «۱۲ آبان»), converted in `jalali.py` on the server and
`lib/jalali.js` in the browser. "Today" always comes from the server (or `DEMO_TODAY`), never the visitor's computer.

## Tests

`pytest` starts the real app on a temporary folder with a fake model (`tests/fake_llm.py`). The fake model can
misbehave on purpose (make up numbers, return broken JSON, time out), so tests prove the fallbacks work. There is
one test file per assistant, plus tests for privacy, checks, dates, validation, concurrency, the door and access.
Browser tests (Playwright, `frontend/e2e`) walk through every school role.

## Deploy

A push to a `claude/` branch is merged into `main`, and the server pulls it, installs only what changed, restarts,
and checks the app answers; on failure it goes back to the previous commit by itself (`deploy/README.md`).

## Questions you will be asked

**"Did you write this code yourself?"** It was written with an AI coding assistant, working under written rules
(`CLAUDE.md`) that fix where each kind of code lives, what the model may and may not do, and what "done" means. The
product decisions, the rules, the review of every change and the tests that prove behaviour are mine. Every design
decision is written down next to the code, as in this file, so it can be explained and changed by anyone.

**"Why not let the AI do everything?"** Because it cannot be trusted with numbers, dates or rules, and a business
cannot afford a wrong deadline or price. Here the model never computes anything that matters, and what it writes is
checked before anyone sees it.

**"What happens when the model gives a wrong answer?"** The check catches any number it invented and a code-built
text replaces it. Reading pasted text, any value not found in the text is dropped. The screen says when the plain
text was used.

**"What happens when the model or the internet is down?"** The same screens, with code-built texts. Every assistant
works fully with its AI switched off; that is how it is offered for offline installs.

**"Why SQLite and not PostgreSQL?"** One office, a few users, no server to install, one file to back up. Moving to
PostgreSQL later means changing `store.py` of that assistant; the SQL is standard.

**"How do you know it works?"** Each assistant has tests that build its demo, check every planted situation is found
exactly once, check every role's limits, and run the main flow end to end, including the model misbehaving.

**"Show me a bug or a change."** Open the assistant's document: it lists where each rule lives and how to change the
common things (a deadline length, a price factor, a new check), with the test that covers it.
