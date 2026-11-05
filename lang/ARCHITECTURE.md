# The language institute's assistant

A small English institute (آموزشگاه زبان) in week eight of a ten-week term: ten teachers, six rooms, thirty classes,
about 300 learners, and the next term half planned. Four people log in: the manager (`modir`), the secretary
(`monshi`), a teacher (`ostad`) and a learner (`zabanamooz`), password `1234`.

## What it is for

Everything here is the ordinary work of an institute that lives in a paper timetable and an Excel sheet:
- a timetable without clashes, this term's and the next one's, and moving a class without breaking it;
- registration, the placement test for a walk-in, the fee and the calls;
- attendance and marks for the teacher, and online tests marked by code;
- for the learner: where they are on the road, this term's book, the next one, and what to do this week.

## The pieces

| File | What it holds |
|---|---|
| `institute.py` | the institute's name and two people (`lang.json`); nothing else is named in code |
| `curriculum.py` | the road: six levels × two terms, the book and units of each term, fees and book prices; the question bank (48 questions) and the placement test (3 per level) |
| `store.py` | the database `lang.db`: users, terms, classes, enrolments, payments, attendance, tests and attempts, the plan's ticks, contacts, the log |
| `facts.py` | every number: session dates, the timetable's problems and the move grid, the learner's road and weekly plan, marking, today's work per role, the four cards |
| `demo.py` | builds the institute around today with the planted situations (its docstring lists them) |
| `api.py` | `/lang/...`, thin: checks the role, calls `facts`, returns |

Frontend: `frontend/src/lang/` (its own colours in `lang.css`, on `body.lang-app` while it is open).

## Why it is built this way

**The timetable is one rule, used three ways.** `facts.cell_reasons(class, pair, time, room)` says why a class
cannot be in a cell: the room is taken, the teacher teaches elsewhere at that hour, the teacher does not come then,
or the room has fewer seats than the class has learners. `problems()` runs it over a whole term (the manager's
alerts), `move_grid()` runs it over every cell for one class (the green cells in «جدول کلاس‌ها»), and the move and
new-class endpoints run it once more before writing. So the screen, the alert and the server can never disagree.

**The road is data, not a picture.** `facts.road()` turns a learner's enrolments into twelve stations with a state
(done with the mark, skipped by the placement test, current, next, future), the current term's book, unit and
sessions, the next term's book (the same one or a new one, and its price), its classes, and when the road ends if they
go on without a break. `RoadMap.vue` only draws it: a winding line whose rows hold 6, 4 or 3 stations by the width.

**Tests are marked by code.** The browser never gets the right answers (`_paper`). Each answer is saved as it is
picked, so a lost connection loses nothing; the time is the server's (`seconds_left`), and an answer after the
time (with 30 seconds' grace) hands the test in. The placement test is the same machinery: the first level with fewer
than two of its three questions right is where the learner starts.

**The weekly plan comes from the facts.** `week_plan()` reads this week's sessions and the unit each one teaches
(three sessions a unit, the midterm at 10, the final at 20), the skills under 60% in this term's online tests, the
last absence and any open test. Each item has a stable key, so its tick lasts the week.

**Privacy by role.** A teacher opens only their own classes and sees no phones or fees; a learner sees only their
own road, plan, tests and fee; the office runs only placement attempts. The floating assistant answers each role
from that role's own facts.

**The model writes three things only:** the manager's morning summary, the learner's two-sentence note and the
floating assistant's answers. Each is checked with `only_known_numbers` and has a code-built fallback, so with the
card's AI switched off the screens look the same. Messages to learners (absences, fee, registration, placement
result, a class that moved) are written by code and sent by a person.
