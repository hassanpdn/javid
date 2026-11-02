# Taking an assistant to a real customer (on their own computer, without internet)

Hassan's choice (2026-11-02): a customer's assistant runs on a computer in their own office, with no internet. One
computer is always on and keeps the program and the data; everyone else in the office opens it in a browser over the
office network. Nothing leaves the office.

Read this file before any step for a real customer, and tell Hassan the limitations that apply before starting. Today
every assistant is a demo; the "Before the first customer" list below is not done yet.

## What works without internet, assistant by assistant

| Assistant | Without internet | What does not work, and what to tell the customer |
|---|---|---|
| Law office (`law/`) | Everything | Nothing missing. The courts' system (ثنا) is still read on the internet by a person; its notices are pasted in. Best first customer. |
| Deed extraction (`deed/`) | Everything | Tesseract and poppler must be installed with the program; a fast processor helps. |
| Fabric wholesaler (`fabric/`) | All but the website | «سایت فروشگاه» needs a public server: leave it out. The three Excel files, the phone desk, checks and reports work. |
| Real estate (`estate/`) | All but two parts | «سایت بنگاه» needs a public server: leave it out. Agents out on a visit cannot reach the office computer from their phone. |
| Dental clinic (`dental/`) | Everything | Reminders and follow-ups are drafts the secretary sends from the clinic's own phone; sending SMS from the program would need an SMS service on the internet: leave it out. |
| School (`school`, the main app) | Staff only | Parents and students work from home, so they cannot reach a computer inside the school. Offer it with «چه کسانی وارد شوند» set to staff only. The documents' search needs its index built before installing (see below). |

The AI, without internet:
- Off: every assistant works with text built by code (`offline.py`, the fallbacks in each `api.py`). This is the
  default for a local install.
- On, with a model on the same computer (Ollama): needs a Mac with at least 32 GB of memory or a PC with a 16 GB
  graphics card. Most small offices do not have one.
- AvalAI or any hosted model needs internet: not possible in this setup.

## Several people, each on their own computer: the office network, not the internet

Each person (the manager, the office, the counselor, each teacher) uses their own laptop or phone; none of them holds
data. One computer (the server) runs the program and keeps the database; the others open it in a browser at that
computer's address on the office network, e.g. `http://192.168.1.10:8000`. Data goes between them through the
school's router and Wi-Fi, which work without an internet subscription.
- Needed: one router (or switch plus Wi-Fi access points) covering every room where someone works; the server plugged
  in by cable; a fixed address for the server (set in the router) so its address never changes. A short name such as
  `madreseh.local` can be set in the router so nobody types numbers.
- The server must listen on the office network (0.0.0.0, not 127.0.0.1 as on the live site) with the port opened in
  the Windows firewall for the private network only.
- The Wi-Fi must have a strong password (WPA2 or WPA3): the program runs on plain http inside the building, so an open
  Wi-Fi would let anyone nearby read logins. Teachers' phones join the same Wi-Fi.
- Not a copy on each laptop kept in step with the others: two copies of the same records drift apart and their
  conflicts lose data. One database, on one computer, is the only safe way.
- Only inside the building: a teacher at home cannot reach it. Reaching it from outside needs the internet (a VPN or a
  public server), which this setup does not use.
- The server must be on whenever anyone works. If it is off, nobody can work; nothing is lost.

## Limitations that apply to every local install

- One computer holds everything. If its disk fails without a backup, the office loses its records. Backups are not
  optional (see below).
- The computer must stay on and must restart the program by itself after Windows restarts it for updates.
- The data on that computer is sensitive (cases, clients, students). Without disk encryption (BitLocker), a stolen
  computer is a leak.
- No internet means no remote support: help is by phone or a visit, and updates arrive on a USB stick.
- SQLite allows one writer at a time. That is fine for an office of a few people; it is not for dozens writing at once.
- A program installed on a customer's computer can be copied. A licence key tied to the computer is needed.
- Today a change to `db.py` or `seed.py` wipes the demo's data (see CLAUDE.md, Deploy). With a customer's data that
  is unacceptable: every schema change must become a migration that keeps the data.
- The school's document answers read the articles from the vector store (`db/`), which `ingest.py` builds with the
  embedding model. Build it before installing and ship it with the program, or the answers have nothing to read.
- The computer's clock is the source of "today" (deadlines, attendance). A wrong clock gives wrong deadlines: check it
  when installing.

## Check with someone from the trade before showing it to a real customer

These are guesses made while building the demo. Remind Hassan of them before any step for a customer of that kind.
- Law office: the number of days for each kind of notice, the shape of a real notice from ثنا (the reader was written without a real sample), this year's lunar holidays.
- Dental clinic: the price list (made up), the working hours and length of each service, the thresholds (14 days before a plan needs a call, two no-shows in 90 days), official holidays (not counted yet), and whether a clinic wants the follow-up message at all or calls instead.
- Pharmacy (not built yet): every insurance rule that leads to deductions (کسورات) must come from a pharmacist (مسئول فنی).
- Accounting office (not built yet): every filing deadline (اظهارنامه, سامانه‌ی مؤدیان, insurance lists) must come from an accountant.
- Distribution, contractor, freight (not built yet): their documents and numbers (pre-invoice, صورت‌وضعیت and فهرست‌بها, waybill) must be checked against real ones.

## Before the first customer (once per assistant; none of this exists yet)

1. Production mode: start empty instead of building demo data; no setup form that rebuilds everything; no door page,
   assistants page or `RESET_ON_LOAD`.
2. Real accounts: each person with their own username and password, and the owner can add and remove people. No
   password `1234`, no one-click login.
3. Importing what the customer already has, from Excel (the law office: open cases and pending notices). The hardest
   and most important part: no office starts from nothing.
4. Migrations: a numbered list of schema changes applied in order, keeping the data, with a test.
5. A test that the assistant works with the network cut off and the AI off, end to end, and that it makes no outside
   request at all.
6. Packaging: one Windows installer that brings Python, the program and (for the deed assistant) Tesseract, runs it
   as a background service that starts with Windows, and listens only on the office network. This likely needs a new
   packaging tool: ask Hassan before adding it.
7. Nightly backup to a second disk or a USB stick, kept for 30 days, and a tested way to restore it.
8. A licence key tied to the computer, checked without internet, renewed yearly.
9. Updates on a USB stick: a new installer that keeps the data and applies the migrations.
10. A log file the customer can send by phone or USB when something goes wrong.

## Installing for one customer

1. First conversation: how many people, does anyone work outside the office, where the data is today (notebook,
   Excel, other software), AI off or a local model.
2. Check the computer: Windows 10 or 11, about 8 GB of memory, an SSD, always on; a fixed address on the office network;
   the clock and time zone right (Tehran).
3. Install, name the office, make each person's account.
4. Open the program's port in the Windows firewall for the office network only; turn on BitLocker.
5. Import their data with them, and check a few records together.
6. Set up the nightly backup and restore it once to be sure.
7. Half an hour of training per role (the first-visit guides are already in the panels).
8. Agree on support (phone, visits), updates by USB, and the yearly licence.
