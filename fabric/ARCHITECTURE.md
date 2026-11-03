# Fabric wholesaler assistant: architecture and the reasons behind it

The whole application is described in [../ARCHITECTURE.md](../ARCHITECTURE.md). This file is only the fabric wholesaler.

## In one minute

A Tehran fabric wholesaler with customers all over Iran runs the business on three Excel files (stock, sales,
accounts) and the phone. Problems: cheques that bounce, customers over their credit, a fabric about to run out, stock
that never sells, next week's cheques the bank cannot cover. And this wholesaler had a theft: an invoice removed from
the sales file while the fabric still left the warehouse, and an evening's cash that never reached the bank.

The assistant reads the three files as they are (messy), checks them against each other, takes phone orders, and
shows the owner every morning what needs attention, with the sum behind every number.

## The demo story

1. Log in as the owner. The files were read and «دستیار موقع خواندن فایل‌ها این‌ها را مرتب کرد» lists what it
   cleaned: a customer written three ways, Persian digits, a hand-typed total row.
2. Today's work: the biggest buyer with a bounced cheque still ordering, a customer over his limit, a fabric with
   three days of stock left, next week's cheques not covered.
3. «تطبیق»: the three files against each other. A missing invoice number, a fabric short in stock by exactly what
   that invoice held, one day's cash short. Every finding shows its sum and the sheet each part comes from, never a
   name.
4. As the seller, take a phone order: the order goes into all three files at once, and the owner sees it live.
5. «سایت فروشگاه»: be a customer; the website assistant takes an unpaid order; the shop gets a toast.

## The shape

```
 OwnerPanel / SellerPanel / AccountantPanel / ShopView
        │
        ▼
 fabric/api.py (/fabric/...)        fabric/shop.py (/fabric/shop/..., the website)
        │                                  │
        ▼                                  ▼
 fabric/facts.py: money, customers, alerts, report, reconcile()      llm.py (text only, checked)
        │
        ▼
 fabric/store.py → fabric.db   ◄── fabric/excel.py reads (and writes) fabric_files/انبار.xlsx, فروش.xlsx, حسابداری.xlsx
```

| File | What it does |
|---|---|
| `business.py` | The wholesaler being shown and its people. |
| `excel.py` | Builds four months of business into three workbooks, reads them back like a stranger's files (noting each fix), and writes a confirmed sale into all three. |
| `store.py` | The database: a copy of the files, plus what the app adds (invoices, reminders, import notes, events). |
| `facts.py` | Every number: money words, stock, debts, cheques, alerts, the report, and the four reconciliation checks. |
| `api.py` | The panels' routes, `_written()` (model text checked, code text otherwise), `make_invoice()`. |
| `shop.py` | The website's ordering conversation. |

## Why the Excel files stay

A traditional wholesaler will not give up their files on day one. So the files remain the source: the assistant
reads them, and writes a phone sale back into them, so the owner can still open Excel and see the same truth.

## The rules, in code

- **Money words** (`money()`): «۱۲۸ میلیون تومان», the way the bazaar says it. Every amount the model sees is
  worded this way, so a number it copies can be matched exactly by `checks.only_known_numbers`.
- **Reconciliation** (`reconcile()`), five checks from numbers alone:
  - stock: opening + deliveries − sold = on the shelf, per fabric;
  - invoice numbers have no gaps;
  - each day's cash sales = that day's deposit in «صندوق»;
  - every sale paid by cheque has its cheque in accounts;
  - the warehouse keeper's latest shelf count of each fabric (30 days) = what the stock file said at that moment.
- **Customer warnings**: bounced cheque, over the credit limit, quiet for much longer than usual.
- **Next week's cheques**: incoming and outgoing due in seven days against the bank balance.

## What the model does

It reads which fabric and how many from a phone note or a website message (prices, stock and totals are written by
code), and writes the morning summary and reminder messages, checked against computed facts. It never prices or
totals. With the AI off, everything works with code-built texts.

## Why it is built this way

- **Findings show sums, not suspects.** A theft check that names a person is an accusation; one that shows «اول دوره
  + ورود − فروش ≠ موجودی» lets the owner see it.
- **Every change is logged with who and when**, and the seller does not see the checks or the log.
- **The warehouse keeper (انباردار, `anbardar`) is not the seller.** The one who hands fabric over is not the one who
  writes the invoice. The keeper's panel (`WarehousePanel.vue`, `/fabric/warehouse/...`) has today's invoices with
  fabric, rolls and meters to mark handed over (with a note when something differed), goods received (into the stock
  file's «ورود کالا» sheet and the shelf row, so the stock check still adds up) and shelf counts. Counts are blind (the
  file's number shows only after saving) and never change the stock: a difference goes to the owner's «تطبیق». The
  server leaves prices out of `/fabric/stock` for this role; customers, money, files, checks and the log are closed to
  it, and its assistant answers only stock questions.
- **A website order is not an invoice** until it is paid, so it never touches stock or the reconciliation early.

## Questions you will be asked

- *"What if my files look different?"* The reader expects these three files' columns; a real customer's files are
  mapped once at install (`PRODUCTION.md`). Odd values are cleaned and listed, never silently changed.
- *"Can the browser change a price?"* No: a confirmed order is re-priced on the server from the stock file
  (`test_confirm_ignores_prices_from_the_browser_and_refuses_too_much`).

## How to change common things

| Change | Where | Test |
|---|---|---|
| A new reconciliation check | a `*_check()` in `facts.py`, add it to `reconcile()` | `test_the_three_files_are_checked_against_each_other` |
| A new customer warning | `customer_warnings()` in `facts.py` | `test_owner_sees_every_planted_situation` |
| A planted situation | `PLANTED` in `excel.py` | `test_owner_sees_every_planted_situation` |

## Tests

`tests/test_fabric.py` (12): reading the files and reporting the clean-up; every planted situation; model numbers
checked; roles; a phone order written into all three files; prices from the browser ignored; a broken upload changes
nothing; the reconciliation; the event log; the report's sources; the website's unpaid order and returning customer.
