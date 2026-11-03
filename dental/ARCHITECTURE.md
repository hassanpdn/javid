# Dental clinic assistant: architecture and the reasons behind it

The whole application is described in [../ARCHITECTURE.md](../ARCHITECTURE.md). This file is only the dental clinic.

## In one minute

A Tehran dental clinic with a dentist and a secretary. Money is lost in two quiet ways: empty chairs (a patient who
does not come, an hour freed by a cancellation nobody filled) and treatment plans a patient heard about and never
started. A three-implant plan nobody followed up is more money than a month of check-ups.

The assistant keeps the appointment book, finds these leaks every morning and drafts the messages. The secretary
sends them from the clinic's phone; only the dentist marks a treatment done.

## The demo story

1. Log in as the dentist. Today's work: tomorrow's unconfirmed implant appointment, an hour free tomorrow at 17:00
   with three people waiting, a patient who missed twice and is booked again, a 114-million implant plan with no call
   for 35 days.
2. «دادن به فهرست انتظار» books the free hour for someone on the waiting list in two clicks.
3. «پیام پیگیری» on the implant plan: a short, polite message with no price and no pressure, ready to copy.
4. «بررسی‌ها»: a root canal mostly unpaid for 25 days, a crown plan left halfway.

## The shape

```
 DentalPanel.vue (dentist, secretary)
        │
        ▼
 dental/api.py (/dental/...)  ──►  llm.ask_llm for the morning summary and the plan follow-up (checked)
        │
        ▼
 dental/facts.py: slots, balances, plans, alerts, checks
        │
        ▼
 dental/store.py → dental.db        dental/demo.py builds it        dental/clinic.py → dental.json
```

| File | What it does |
|---|---|
| `clinic.py` | The clinic being shown: name, place, dentist, secretary. |
| `store.py` | Schema, logins, sessions, the event log. |
| `facts.py` | Working hours and slots, whether an appointment fits, balances, plans, today's work, checks, the numbers. |
| `api.py` | Routes: booking, appointment status, reminders, patients, payments, plans, follow-ups, waiting list, the floating assistant. |
| `demo.py` | 150 patients, four months of visits and payments, plans in every state, and the planted situations. |

## Data

`patients`, `appointments` (time, length, service, price, status: booked, confirmed, done, no-show, cancelled),
`plans` and `plan_items` (each step with its tooth and price), `payments`, `waitlist`, `contacts` (follow-up calls and
messages), `events`. In a real clinic these come from the secretary's book and the card machine; the plans from the
dentist's exam.

## The rules, in code

- **Working hours**: Saturday to Thursday, 10-14 and 16-20, in half-hour slots; Friday closed. `fits()` says whether an
  appointment of a service's length can start at a time without crossing the midday break or another appointment.
- **Balance**: what the done appointments cost minus what was paid.
- **A plan waits for a call** when nothing was done, nothing is booked and nobody called in 14 days. Biggest first.
- **A patient who often does not come**: two no-shows in 90 days, with an appointment in the next 7 days.
- **Checks**: a balance left 14 days after treatment; a plan begun and left with nothing booked for 45 days.

## What the model does

It writes the dentist's morning summary and the plan follow-up message, from computed facts only, checked by
`only_known_numbers`, with a code-built text otherwise. The follow-up prompt forbids prices, pressure and medical
claims. The appointment reminder is built by code. With the AI off, the screens are the same.

## Why it is built this way

- **Follow-ups ranked by money** because the secretary has time for a few calls a day; the implant comes before the
  filling.
- **The follow-up has no price** because a price in a cold message scares a patient off; the conversation does that.
- **Only the dentist marks a treatment done**, because that is what creates the debt.
- **No SMS sending** because it needs an internet service; drafts are copied to the clinic's phone (`PRODUCTION.md`).

## Questions you will be asked

- *"Can it send reminders by itself?"* Not in this version, on purpose: a person reads and sends. Adding an SMS service
  is one function, but needs internet.
- *"Where do the prices come from?"* `SERVICES` in `facts.py`: made up for the demo; a clinic enters its own.

## How to change common things

| Change | Where | Test |
|---|---|---|
| Working hours or slot length | `SLOTS`, `open_day()` in `facts.py` | `test_slots_and_money_rules` |
| Services and prices | `SERVICES` in `facts.py` | `test_slots_and_money_rules` |
| When a plan needs a call, no-show limits | `FOLLOW_DAYS`, `NOSHOW_*` in `facts.py` | `test_every_planted_situation_once` |

## Tests

`tests/test_dental.py` (8): every planted situation once; slot and money rules; roles; booking the free hour from the
waiting list (and refusing it twice); confirming clears the alert; a payment settles the balance; the follow-up is
replaced when the model changes numbers; duplicate phones refused.

## Limits

Prices, hours and thresholds are guesses; official holidays are not counted (`PRODUCTION.md`).
