# Eco-lodge assistant: architecture and the reasons behind it

The whole application is described in [../ARCHITECTURE.md](../ARCHITECTURE.md). This file is only the eco-lodge.

## In one minute

A small place to stay (بوم‌گردی), 5 to 20 units, run by a family. Today its bookings come through WhatsApp,
Instagram and booking sites; dates are kept in a notebook, deposits are card transfers checked by eye, and reviews live
on other people's websites. The assistant gives the lodge two things:

1. **A public website on its own address** where a guest sees the units, the free nights and their prices, makes an
   account with a mobile number and a password, asks for a booking, sends a photo of the deposit receipt, follows the
   booking, writes to the host and, after the stay, leaves a review.
2. **The host's panel** (behind the demos' door) where the units, prices, closed nights, bookings, receipts, reviews,
   guests and the website's words are managed, with every morning a list of what waits.

## The demo story

1. Open the website (`/eco`, or its own address). The drawn village at night, a search for dates and people, the
   units with prices, the lodge's story, reviews. Open a unit: its calendar shows each night free or taken, with its
   price; pick the nights and see the price night by night.
2. Log in as the sample guest (09120000000 / 1234): a trip that just ended (the review form is open) and one approved
   and waiting for its deposit (the card number, and a button to send the receipt).
3. Open the panel as the host: two requests (approve one right there), a receipt to check (the photo is beside the
   buttons), an overdue deposit, a guest's question, a three-star review waiting before it is shown, and two stays to
   ask about (the message is ready to copy).
4. «واحدها»: add a photo to a unit, switch a unit off (it disappears from the website), close two nights.

## The shape

```
 Public website (frontend/lodge.html → src/eco/, its own small bundle)      Host's panel (src/lodge/, inside the demos' app)
        │  guest token (src/eco/api.js)                                           │  staff token (lib/api.js)
        ▼                                                                         ▼
 lodge/public.py  /lodge/public/...  (open to anyone; rate limited)        lodge/api.py  /lodge/...  (behind the door)
        └───────────────────────────────┬─────────────────────────────────────────┘
                                        ▼
                         lodge/facts.py: prices, free nights, what waits, numbers
                                        ▼
                         lodge/store.py → lodge.db, lodge_files/ (photos, receipts)
```

app.py lets `/eco` and `/lodge/public/...` past the site's door, and when the request comes to `LODGE_HOST` (the
lodge's own address) it serves only those, so a guest never reaches the demos.

| File | What it does |
|---|---|
| `info.py` | The lodge's name and people, and the website's words, in `lodge.json`. |
| `store.py` | Schema; staff logins and guests' logins kept apart; the event log. |
| `facts.py` | Night prices, the shortest stay over a weekend, what is free, the refund rule, what waits, the numbers. |
| `api.py` | The host's routes: units, photos, closed nights, calendar, bookings and their steps, reviews, guests, the website's words. Also the image check (`save_image`). |
| `public.py` | The website's routes: the lodge, a unit and its calendar, search, accounts, a booking request, receipt, cancel, messages, review. |
| `demo.py` | 12 units, four months of stays with reviews, two months ahead, the planted situations, the sample guest. |

## A booking's life

```
 requested ──host approves──► approved ──guest sends receipt──► paid ──host confirms──► confirmed ──stay ends──► review
     │                            │  (deposit due within N hours)   │ «not matching» → back to approved
     └─host rejects──► rejected   └─ either side cancels ──► cancelled (refund by the rule)
```

A request already holds its nights, so two guests can never ask for the same nights at once. Only a person moves a
booking forward: the host approves, the host confirms after seeing the money in the account.

## The rules, in code

- **A night's price**: the unit's price, or its weekend price on Wednesday and Thursday nights, plus a set amount for
  each person beyond its beds (up to its capacity).
- **Weekend stays**: a stay with a Wednesday or Thursday night is at least 2 nights (a setting).
- **Deposit**: 50% (a setting), due 24 hours after approval or before arrival, whichever is first.
- **Cancellation**: more than 7 days before arrival 90% of the confirmed deposit comes back, 3 to 7 days 50%, less than
  3 nothing. The money goes back by hand; the panel says how much.
- **Feedback**: a stay that ended in the last 30 days with no review appears in the host's list; the guest's panel
  opens its review form the day the stay ends. A review is shown only after the host approves it; the host can reply.

## Safety on a public website

- A guest's id comes from their token, never from the request; a guest who asks for another's booking gets «not
  found». A guest's token never opens the panel, and the panel's never acts as a guest.
- Passwords are hashed (the same hashing as every login here). Logins, sign-ups, bookings and writes are limited per
  address per minute, so a script cannot try passwords or fill the calendar.
- Two open requests per guest at most.
- Photos: only JPEG or PNG by their first bytes, at most 6 MB, shrunk to 1600 px and saved again as JPEG (which drops
  anything hidden in the file). Receipt photos are never served publicly; the host sees them inside the booking.
- Reviews show only the guest's first name.
- A banner on every page says it is a demo, and the card number is a placeholder: nobody should pay anything.

## What the model does

Only the host's morning summary and the panel's floating assistant, from computed facts, checked by
`only_known_numbers`, with code-built text otherwise. The website itself has no model: a guest's booking is made of
choices (dates on a calendar, a unit, the people), so nothing needs reading. Messages to guests are built by code.

## Why it is built this way

- **A separate page for the website** (`lodge.html`): a guest downloads about 10 KB of its own code, not the panels.
- **Not reset on each visit**, unlike the other demos: guests make accounts and reviews there (Hassan's choice).
- **Mobile number and password**, not a one-time SMS code: SMS needs a paid service on the internet (Hassan's choice;
  it can be added later).
- **Card transfer with a receipt photo**, not an online payment gateway: a gateway needs a merchant account (Hassan's
  choice). The host still checks the money arrived before confirming.
- **Drawings, not photos from the internet** (Hassan's choice): their rights are clear. The host adds real photos
  from the panel.

## Questions you will be asked

- *"Can two guests book the same night?"* No: a request holds its nights, and every request and approval checks
  the nights again.
- *"Can a guest see someone else's booking or a receipt?"* No; tests try both.
- *"What stops a fake receipt?"* The host confirms only after seeing the deposit in the account; «با واریزی جور
  نیست» sends the guest back to paying, with a message.

## How to change common things

| Change | Where | Test |
|---|---|---|
| Deposit, its hours, extra person, shortest weekend stay | «متن سایت» page, or `DEFAULTS` in `facts.py` | `test_price_rules` |
| The cancellation rule | `refund()` in `facts.py` | |
| What counts as waiting for the host | `alerts()` in `facts.py` | `test_every_planted_situation` |
| The website's look | `frontend/src/eco/eco.css`, the drawings in `Art.vue` | |

## Tests

`tests/test_lodge.py` (9): the planted situations; the public website shows only active units and shown reviews
with first names, and the panel is not public; a guest books, the host approves, the guest sends a receipt, the host
confirms; a guest cannot touch another's booking, a guest's token does not open the panel, a review once and only
after the stay, shown after the host's approval; wrong passwords and too many tries; switching a unit off and closing
nights; photos shrunk and served, receipts never public; the price rule.

## Limits

Prices, rules and texts are the demo's own. No SMS, no online payment, no sync with booking sites (each needs the
internet and a contract). The website's address needs DNS, nginx and a certificate once on the server
(`deploy/README.md`).
