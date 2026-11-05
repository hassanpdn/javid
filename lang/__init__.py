"""The language institute's assistant (دستیار آموزشگاه زبان): beside the others, with its own institute details,
database and logins.

institute.py   the institute this demo is for (name, place, the manager, the secretary)
curriculum.py  the road every learner walks: levels, terms, the book of each term, and the question bank of the tests
store.py       its own SQLite database (lang.db): people, terms, classes, enrolments, sessions, attendance, payments,
               online tests and their attempts, the weekly plan's ticks, messages and the log
demo.py        builds an institute half way through its autumn term around today, with planted situations to find
facts.py       every number and date: session dates, the timetable and its clashes, the learner's road, the weekly
               plan, grading of the tests, today's work for each role
api.py         the /lang/... endpoints
"""
