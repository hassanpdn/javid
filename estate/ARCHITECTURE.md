# Real estate agency assistant: architecture and the reasons behind it

The whole application is described in [../ARCHITECTURE.md](../ARCHITECTURE.md). This file is only the agency.

## In one minute

A neighbourhood agency in west Tehran with an owner and two agents, sale and rent. What goes wrong in a traditional
agency: listings lost or entered twice, sold units still offered, buyers matched from memory, owners left without
news, prices guessed, and deals done around the agency once a customer has seen a unit enough times.

The assistant turns pasted ads and messages into listings and requests, matches them by code, checks a price against
the agency's own past deals, and shows the owner what slipped.

## The demo story

1. Log in as the owner. Today's work: a new listing that fits an old buyer nobody called, tomorrow's unconfirmed visit,
   an owner without a report for 41 days, a listing with no call to its owner for 52 days.
2. Paste a Divar ad into «فایل جدید»: the form fills itself, each value with its words, and the look-alike unit (the
   same flat entered by the other agent) appears before saving.
3. Open the overpriced listing: «از کجا؟» lists the agency's deals in that neighbourhood and the median per m².
4. «بررسی‌ها»: a unit withdrawn days after a customer's third visit, the customer then marked lost; a commission
   well under the tariff.
5. «سایت بنگاه»: be a buyer; the site shows fitting units (never the owner's name or address) and takes a number.

## The shape

```
 OwnerPanel / AgentPanel / SiteView
        │
        ▼
 estate/api.py (/estate/...)        estate/site.py (/estate/site/...)
        │            │                     │
        ▼            ▼                     │
 estate/facts.py   estate/read.py ◄────────┘   (rules or model; every value checked against the text)
 match, price_check, convert, commission, alerts, checks
        │
        ▼
 estate/store.py → estate.db        estate/demo.py        estate/agency.py → estate.json
```

## The rules, in code

- **Match** (`match()`): the neighbourhood is required; the budget may be passed by up to 8% (room to bargain);
  for rent, a deposit far above what they have is no match, and deposit and rent are compared as one monthly amount;
  one room fewer or an area up to 15% smaller lowers the score and is said in words; a missing feature costs points.
  Under 45 points is no match. Every match comes with its reasons and what is missing.
- **Price check** (`price_check()`): price per m² (for rent, the whole monthly rent with the deposit converted)
  against the agency's own deals in that neighbourhood in the last year, similar age when there are three; under three
  deals, no verdict.
- **Deposit and rent** (`convert()`): one becomes the other at the agency's monthly rate (default 3%).
- **Commission** (`commission()`): from each side, by the agency's settings (default 0.5% of a sale, 25% of a month's
  rent), to be checked against the union's tariff.

## What the model does

It reads pasted listings and requests (every value must be in the text, else empty) and writes the owner's report
from computed facts, checked by `only_known_numbers`, with a code-built text otherwise. It never matches or prices.

## Why it is built this way

- **Prices against the agency's own deals**, not a public price list, because those are the numbers the owner trusts
  and can check deal by deal.
- **The website never shows an owner's name, phone or exact address**, and leaves out listings nobody confirmed with
  their owner in 30 days, so it never offers a unit that is already sold.
- **The «deal around the agency» check describes a pattern** (third visit, then withdrawn, then the customer lost) and
  stops there: the owner decides what it means.

## Questions you will be asked

- *"Why not use Divar's prices?"* They are asking prices, not deals; and they need the internet. The agency's own
  deals are what it actually closed.
- *"How does it find the same flat entered twice?"* Same kind, neighbourhood and floor, an area within 3 m², and the
  same owner phone or street (`duplicates()`).

## How to change common things

| Change | Where | Test |
|---|---|---|
| Matching weights | `match()` in `facts.py` | `test_new_listing_meets_its_buyers` |
| Price flag limit | `PRICE_FLAG` in `facts.py` | `test_price_check_flags_the_overpriced_unit_with_its_sum` |
| Rate and tariff | the settings page | `test_convert_deposit_and_rent`, `test_deal_under_tariff_shows_in_the_checks` |
| Reading a new kind of ad | `read.py` | `test_nothing_is_made_up_from_the_text` |

## Tests

`tests/test_estate.py` (15): every planted situation; agents without checks; the price check with its sum; a pasted
listing finding its duplicate; nothing made up; calls clearing alerts; matching; visits; the tariff check; stale
listings; the owner's report and assistant answers checked; deposit and rent; the website without owner details.
