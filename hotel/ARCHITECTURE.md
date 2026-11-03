# Hotel assistant: architecture and the reasons behind it

The whole application is described in [../ARCHITECTURE.md](../ARCHITECTURE.md). This file is only the hotel.

## In one minute

A luxury hotel on the Caspian coast (Nowshahr), 80 rooms in three types, 6 suites and 4 villas. Its pain is the
busy day: Nowruz and summer mornings, when the desk has 25 arrivals, 20 departures, rooms not ready and the phone
ringing. Money leaks quietly: a room sold twice, a deposit that never came while the room was held, one empty night
left between two stays that nobody will ever buy, a guest who leaves with the minibar unpaid.

The assistant does reservations to check-out in one panel. It prices, counts rooms left, suggests a room, finds
problems and drafts messages. The operator confirms, cancels and charges. Nothing that touches a guest or money
happens without a person pressing a button.

## The demo story (five minutes)

1. Log in as the manager. The home page lists today's work, most urgent first: room 107 given to two bookings, next
   Thursday oversold by two, a VIP arriving at 14:00 to a dirty suite, two deposits past their deadline, a guest
   leaving with 7.8 million unpaid, one empty night between two stays. Open «از کجا؟» on any number.
2. «رزرو از روی پیام»: paste «۱۵ تا ۱۸ آذر یک اتاق رو به دریا برای دو بزرگسال و یک بچه‌ی ۶ ساله…». The form fills
   itself, each value with the words it came from; every room type shows rooms left and the price night by night.
3. Press «جابه‌جا کن» on the empty night: the later stay moves next door and the night joins a sellable block.
4. «شلوغی»: arrivals by time with their room's state, the rooms housekeeping must do first, and tomorrow's rooms given
   in one click. Log in as housekeeping on a phone and press «تمیز شد»: the desk sees it at once.
5. «سایت هتل»: be the guest. Ask for two nights; the site shows free rooms with prices and makes a tentative booking.
   The desk gets a toast.

## The shape

```
 HotelPanel.vue (manager, reservations, front desk)      HousekeepingPanel.vue (phone)      SiteView.vue (guest)
        │                                                         │                              │
        ▼                                                         ▼                              ▼
 hotel/api.py  (/hotel/...: roles, input checks)                                         hotel/site.py (/hotel/site/...)
        │                    │                                                                   │
        ▼                    ▼                                                                   │
 hotel/facts.py         hotel/read.py ── llm.ask_json (optional, checked against the text)        │
 prices, availability,                                                                            │
 room suggestions,      ◄──────────────────────────────────────────────────────────────────────────┘
 alerts, checks, report
        │
        ▼
 hotel/store.py → hotel.db          hotel/demo.py builds it around today          hotel/info.py → hotel.json
```

## Files

| File | What it does |
|---|---|
| `info.py` | The hotel being shown: name, place, the four people. From `hotel.json`; the setup form writes it. |
| `store.py` | The database schema, connection, logins and sessions, and `log()` (every change, who and when). |
| `facts.py` | Every number and rule: prices, availability, room suggestions, folios, refunds, today's alerts, the manager's checks, the report, the busy-day page. No web code, no model. |
| `read.py` | A booking request from pasted text. Rules read it; the model may only add a name, room type or meals whose words are in the text. |
| `api.py` | The routes. Thin: validate, check the role, call `facts`, write, log. Holds `make_booking()`, used by the website too. |
| `site.py` | The website conversation inside the panel («سایت هتل»). Asks only what it needs, shows free rooms with prices, makes a tentative booking. |
| `public.py` | The real public website's API (`/hotel/public/...`, on hotel.pudineh.com): search, guests' own accounts, a tentative booking, the deposit receipt, cancelling. |
| `frontend/src/hsite/` + `frontend/hotel.html` | The public website, its own small page (borrows the eco-lodge website's layout, `eco/eco.css`, in the hotel's colours). |
| `demo.py` | Four months of stays and two months ahead, with the planted situations listed at its top. |
| `frontend/src/hotel/` | The screens. They show what the server sends and never compute a business number. |

## Data

| Table | Holds | In a real hotel it comes from |
|---|---|---|
| `rooms` | number, type, floor, state (clean, dirty, inspected), out-of-order dates | entered once at install |
| `guests` | name, mobile, national ID, VIP, notes (allergies, preferences) | the first booking; moved over from old software or Excel |
| `bookings` | guest, room or only its type, dates, people, children's ages, meals, source, agency, status, deposit deadline, each night's price | the reservations desk, booking sites (typed in), the website |
| `charges` / `payments` | the folio: nights, restaurant, minibar, spa...; deposits, payments, refunds | the desk; closing the day posts each night |
| `agencies` / `allotments` / `groups` | agencies, booking sites and companies; blocks of rooms with a release date | contracts, entered once |
| `tasks` | guests' requests and repairs | the desk and housekeeping |
| `room_log` | every change of a room's state | housekeeping's phone |
| `closes` | each closed day: nights posted, cash expected and counted | the night's close |
| `events` | who did what and when | everything above |

A booking's nights run from the arrival day to the day before departure. A booking may have a type and no room yet:
rooms are given the day before arrival, like a real desk does.

## The rules, in code

**Price of a night** (`facts.quote`): base price of the type × season (Nowruz 1.6, summer 1.3, quiet months 0.8)
× 1.2 on Wednesday and Thursday nights, + extra bed for each person beyond the type's beds, + meals per adult (half
for a child over 6) for half or full board, − the agency's or the manual discount. Children under 6 are free and take
no bed. The booking keeps each night's price, so a later price change never changes a sold booking.

**Rooms left** (`facts.availability`): for each type, the sellable rooms (not under repair) minus the active bookings
of that type, on every night of the stay; the answer is the fullest night. Counting by type, not by room, is how
hotels sell: you sell "a sea-view double", and give the room later.

**Which room** (`facts.suggest_rooms`): of the rooms free for every night, prefer one where the stay sits right after
or right before another (+2 each), never one that leaves a single empty night (−3), the room the guest had last time
(+3), a high floor for a VIP (+1), and a room ready now for an arrival today (+1). Each suggestion says why.

**Deposit and cancellation**: a tentative booking waits for 30% until tomorrow (or the day before arrival); paying it
makes the booking confirmed. Cancelling returns 90% of what was paid with more than 7 days left, 50% with 3 to 7, none
under 3 (`facts.refund`).

**Closing the day** (`POST /hotel/close`): tonight's price goes on the folio of every room in the house, and the
cash counted is set beside the day's cash payments. A difference is kept and shown in the manager's checks.

**Today's work** (`facts.alerts`): a VIP arriving to a room not ready; deposits past their deadline; nights sold
beyond the rooms of a type; one room given to two bookings; a booking in a room under repair; two bookings with the
same mobile on overlapping dates; an agency block released within two days with rooms still unnamed; a guest leaving
today with something unpaid; a returning guest with notes arriving within three days; a single empty night with a
move that closes it; a guest's request open over an hour; a room free again for someone on the waiting list.

**The manager's checks** (`facts.checks`): a discount over the limit, a booking cancelled after check-in, a guest
checked in to a room housekeeping marked dirty, a day whose cash did not match. They show the records; they never
name a culprit.

## What the model does, and what it never does

- It may read a pasted booking request, but only a name, a room type or meals, and only if its words are in the text.
  Dates, people and phone numbers are read by rules alone (`read.py`).
- It writes the manager's morning summary from computed facts; `checks.only_known_numbers` rejects it if it has any
  number not in those facts, and a code-built summary is shown.
- It answers the floating assistant's questions from a block of computed facts, checked the same way.
- It never prices, counts, chooses a room, confirms, cancels or charges. Messages to guests (confirmation,
  thank-you) are built by code.
- With the AI off or slow, every screen is the same and the texts are code-built.

## Why it is built this way

- **Rooms by type, room given the day before.** It is how hotels sell, and it keeps rooms free to be arranged back
  to back. The tape chart shows bookings without a room separately.
- **A single empty night is treated as lost money.** Almost nobody books one night wedged between two stays. The
  room suggestion avoids making them, and the alert offers the move that closes one.
- **Tentative bookings expire.** On busy days the biggest leak is a room held for someone who never pays.
- **The check-in refuses a dirty room** unless the manager forces it, and a forced one shows up in the checks.
- **The police's guest registration and booking sites are not connected.** Both are on the internet, and a real
  customer installs offline. The desk gets a ready list to copy. This is written in `PRODUCTION.md`.
- **The public website books a room type, never a room, and the booking waits for its deposit.** The guest pays card
  to card and sends a photo of the receipt; a person at the desk looks at the bank and accepts it (the deposit is
  recorded, the booking confirmed) or turns it down. No gateway: Hassan's choice for the eco-lodge, kept here.
- **Guests see only what they booked with their account.** No text message checks a mobile number, so a phone booking
  under the same number stays with the desk.
- **The hotel is not reset on each visit any more,** because its website has guests' accounts. The demo is still
  rebuilt each day around today; accounts are not wiped and bookings still to come are put back without a room
  (`store.keep_site` / `restore_site`).
- **Housekeeping has its own phone page** with no prices, phones or bookings: it needs only the rooms, in the order to
  do them.

## Questions you will be asked

- *"How is the price of 55 million worked out?"* «از کجا؟» next to it shows each night: base, season, weekend, extra
  bed, meals, discount.
- *"What if two people book the last room at once?"* Every booking re-checks rooms left inside its write; the second
  gets «جا ندارد». The demo plants a room given twice to show the alert that catches it if it ever happens by hand.
- *"Can I oversell on purpose?"* Only the manager (`over: true`), and the report says how far is safe from the
  no-show rate of the last 90 days.
- *"Does it connect to Jabama or Snapptrip?"* Not in this version (internet, contracts). Their bookings are typed or
  pasted; a booking site's reference is kept and searchable.

## How to change common things

| Change | Where | Test |
|---|---|---|
| A price, the deposit, the discount limit | «قیمت‌ها» page, or `DEFAULTS` in `facts.py` | `test_price_and_rules` |
| Season factors or weekend nights | `season()` and `weekend()` in `facts.py` | `test_price_and_rules` |
| The cancellation rule | `refund()` in `facts.py` | `test_cancel_follows_the_rule` |
| How rooms are suggested | `suggest_rooms()` in `facts.py` | `test_the_gap_closes_by_moving_the_later_stay` |
| A new item in today's work | `alerts()` in `facts.py`, plant it in `demo.py` | `test_every_planted_situation_once` |
| A new check for the manager | `checks()` in `facts.py` | `test_every_planted_situation_once` |

## Tests

`tests/test_hotel.py` (11 tests): every planted situation found exactly once; price and season rules; each role's
limits; a pasted message to a quote, a booking, its deposit and confirmation message; check-in refused for a dirty room
and check-out refused with money left; a room given twice fixed by moving; the empty night closed; tomorrow's rooms
given and the day closed; cancellation by the rule; the morning summary replaced when the model makes up numbers; the
website making a tentative booking.

## Limits

All prices, factors and rules are the demo's own and must be confirmed by a hotelier (`PRODUCTION.md`). Official
holidays are not priced yet. Allotments do not hold rooms out of sale. No card-key locks, restaurant or spa modules:
their charges are typed on the folio.
