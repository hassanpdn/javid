# Law office assistant: architecture and the reasons behind it

The whole application is described in [../ARCHITECTURE.md](../ARCHITECTURE.md). This file is only the law office.

## In one minute

A Tehran law office: a lawyer, an associate, a secretary, about 60 open cases. Notices arrive from the courts'
system (ثنا), and each starts a deadline: 20 days to appeal, 10 to correct a petition, 7 to object to an expert. Those
deadlines live in a notebook or someone's head. One missed deadline is a lost case and an angry client.

The assistant reads a pasted notice, finds its case, counts the last day with Fridays and holidays, and shows every
morning what is due, what passed and which client has heard nothing.

## The demo story

1. Log in as the lawyer. Today's work: a correction deadline that passed yesterday, an appeal due the day after
   tomorrow, a hearing tomorrow, a case idle for 75 days, a client without news for 40 days.
2. «ثبت ابلاغیه» → «یک نمونه از پرونده‌های دفتر» → «خواندن ابلاغیه»: kind, case number, branch and date are read, each
   with its words; the case is found by its number. Save: the last day appears; «از کجا؟» shows how it was counted.
3. Open the appeal whose twentieth day is a Friday: the last day moved to Saturday, and the explanation says so.
4. «بررسی‌ها»: an appeal filed after its last day, a notice entered five days after it was served.
5. «نوشتن گزارش» on a case: a short message to the client, which the lawyer reads and sends.

## The shape

```
 LawPanel.vue (lawyer, associate, secretary) ──► law/api.py ──► law/facts.py ──► law/store.py → law.db
                                                     │
                                                     ├──► law/read.py (rules, optional model, checked against the text)
                                                     └──► llm.ask_llm (summary, client report, questions; checked)
```

| File | What it does |
|---|---|
| `office.py` | The office being shown and its three people. |
| `store.py` | Schema, logins, sessions, the event log. |
| `facts.py` | `deadline()`, holidays, today's work, checks, the numbers. |
| `read.py` | A notice from pasted text: kind, case number, archive number, branch, court, dates. |
| `api.py` | Routes: cases, notices, marking work done, deadlines, the client's report, settings. |
| `demo.py` | About 60 cases and the eight planted situations. |

## The deadline rule

The day of service does not count. The last day is service + the days for that kind of notice. A last day on a
Friday or an official holiday moves to the next working day, again and again if needed. Days per kind are settings
(defaults 20, 10, 7). Fixed solar holidays are built in; lunar holidays move every year and are typed in by the office.
Every deadline keeps its explanation («تاریخ ابلاغ… مهلت ۲۰ روز… به‌خاطر جمعه یک روز جلوتر رفت»).

## What the model does

It may fill a notice field the rules missed, only if the value is written in the text. It writes the morning summary
and the client's report from the case's computed facts, checked by `only_known_numbers`, with a code-built text
otherwise. It never counts a deadline.

## Why it is built this way

- **Deadlines by code, with their explanation**, because a lawyer must be able to check the count by hand before
  trusting it.
- **Pasted text, not a connection to ثنا**, because the courts' system needs the lawyer's own login and is on the
  internet; the office copies the notice in.
- **Checks on dates**, not on people: an action after its last day, a notice entered late. They point at the habit
  (check ثنا every day), not at a person.

## Questions you will be asked

- *"Are the deadlines legally right?"* They are the common ones in civil procedure and are settings; a real office
  confirms them before relying on them (`PRODUCTION.md`).
- *"What if the notice text looks different?"* What the rules cannot find stays empty and is filled by hand; nothing
  is guessed.

## How to change common things

| Change | Where | Test |
|---|---|---|
| Days for a kind of notice | «مهلت‌ها و تعطیلات», or `KINDS` in `facts.py` | `test_deadline_rules` |
| Holidays | `solar_holidays()` in `facts.py`, lunar ones in settings | `test_deadline_rules` |
| Reading a new notice format | `KIND_WORDS` and `rules()` in `read.py` | `test_reading_a_notice_matches_its_case_and_sets_the_deadline` |

## Tests

`tests/test_law.py` (10): every planted situation once; Friday and holiday rules; roles; the associate sees only
their cases; reading a notice, matching its case and setting the deadline; nothing made up from an empty notice;
marking done clears the alert and a late action shows in the checks; a hearing needs its time.

## Limits

Deadline lengths and the notice format need a real lawyer's confirmation; lunar holidays are typed in each year.
